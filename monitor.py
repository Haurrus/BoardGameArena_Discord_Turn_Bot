from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import discord
from discord.ext import tasks

from bga_client import BgaClient, BgaClientError, BgaNotPublicError
from database import Database
from i18n import tr
from models import LinkedUser, WatchSubscription
from utils import build_table_url, format_game_name

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ActiveTurnMessage:
    message: discord.Message
    waiting_ids: list[str]


class BgaMonitor:
    def __init__(
        self,
        bot: discord.Client,
        database: Database,
        bga_client: BgaClient,
        poll_seconds: int,
    ) -> None:
        self.bot = bot
        self.database = database
        self.bga_client = bga_client
        self._table_tasks: dict[str, asyncio.Task[None]] = {}
        self._active_turn_messages: dict[int, ActiveTurnMessage] = {}
        self.sync_tables.change_interval(seconds=max(5, poll_seconds))

    def start(self) -> None:
        if not self.sync_tables.is_running():
            self.sync_tables.start()

    def stop(self) -> None:
        if self.sync_tables.is_running():
            self.sync_tables.cancel()
        for task in self._table_tasks.values():
            task.cancel()
        self._table_tasks.clear()
        self._active_turn_messages.clear()

    @tasks.loop(seconds=30)
    async def sync_tables(self) -> None:
        await self._sync_tables_once()

    async def refresh_now(self) -> None:
        await self._sync_tables_once()

    async def _sync_tables_once(self) -> None:
        subscriptions = self.database.list_watch_subscriptions()
        active_table_ids = {subscription.table_id for subscription in subscriptions}
        active_subscription_ids = {subscription.subscription_id for subscription in subscriptions}

        for subscription_id in list(self._active_turn_messages):
            if subscription_id not in active_subscription_ids:
                self._active_turn_messages.pop(subscription_id, None)

        for table_id in list(self._table_tasks):
            if table_id not in active_table_ids:
                task = self._table_tasks.pop(table_id)
                task.cancel()
                LOGGER.info(tr("worker_stopped", table_id=table_id))

        for table_id in sorted(active_table_ids):
            task = self._table_tasks.get(table_id)
            if task is None or task.done():
                self._table_tasks[table_id] = asyncio.create_task(self._run_table_worker(table_id))
                LOGGER.info(tr("worker_started", table_id=table_id))

    @sync_tables.before_loop
    async def before_sync_tables(self) -> None:
        await self.bot.wait_until_ready()

    async def _run_table_worker(self, table_id: str) -> None:
        backoff_seconds = 5
        did_cleanup = False
        while True:
            try:
                subscriptions = self._subscriptions_for_table(table_id)
                if not subscriptions:
                    return

                reference = subscriptions[0]
                if not reference.table_url or not reference.base_url:
                    LOGGER.warning(tr("legacy_watch_without_url", table_id=table_id))
                    return

                table_info = self.bga_client.build_public_table_info(
                    table_id=reference.table_id,
                    table_url=reference.table_url,
                    base_url=reference.base_url,
                    gameserver=reference.gameserver or "",
                    game_name=reference.game_name or "unknown",
                )
                if not did_cleanup:
                    await self._cleanup_stale_table_messages(subscriptions, table_id)
                    did_cleanup = True
                finished_publicly = await asyncio.to_thread(
                    self.bga_client.fetch_public_table_finished_status,
                    table_info,
                )
                if finished_publicly:
                    await self._finalize_finished_table(subscriptions, table_id)
                    return
                current_waiting_ids = self._select_previous_waiting_ids(subscriptions)
                known_player_names = self._merge_player_names(subscriptions)

                async for state in self.bga_client.watch_table(
                    table_info,
                    current_waiting_ids=current_waiting_ids,
                    known_player_names=known_player_names,
                ):
                    current_waiting_ids = state.waiting_ids or current_waiting_ids
                    known_player_names.update(state.player_names)
                    await self._apply_table_state(table_id, reference.game_name or "unknown", state)

                backoff_seconds = 5
            except asyncio.CancelledError:
                raise
            except BgaNotPublicError as exc:
                LOGGER.warning(tr("table_not_public", table_id=table_id, error=exc))
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, 60)
            except BgaClientError as exc:
                LOGGER.error(tr("websocket_error", table_id=table_id, error=exc))
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, 60)
            except Exception:
                LOGGER.exception(tr("unexpected_worker_error", table_id=table_id))
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, 60)

    async def _apply_table_state(self, table_id: str, fallback_game_name: str, state) -> None:
        subscriptions = self._subscriptions_for_table(table_id)
        if not subscriptions:
            return

        merged_player_names = self._merge_player_names(subscriptions)
        merged_player_names.update(state.player_names)
        await asyncio.to_thread(self.database.enrich_linked_users_from_players, merged_player_names)

        if state.is_game_finished:
            LOGGER.info(tr("table_finished_public", table_id=table_id))
            await self._finalize_finished_table(subscriptions, table_id)
            return

        table_packet_id = state.highest_packet_id or max(item.last_packet_id for item in subscriptions)
        LOGGER.info(
            tr(
                "table_state",
                table_id=table_id,
                packet_id=table_packet_id,
                waiting_ids=state.waiting_ids,
                source=state.source,
                details=state.details,
            )
        )

        for subscription in subscriptions:
            previous_waiting_ids = subscription.last_waiting_ids
            waiting_ids = state.waiting_ids if state.waiting_ids is not None else previous_waiting_ids
            current_player_names = dict(subscription.player_names)
            current_player_names.update(state.player_names)
            game_name = subscription.game_name or fallback_game_name

            if not subscription.is_initialized:
                self.database.update_watch_state(
                    subscription_id=subscription.subscription_id,
                    last_packet_id=table_packet_id,
                    waiting_ids=waiting_ids,
                    player_names=current_player_names,
                    is_initialized=True,
                    game_name=game_name,
                )

                if waiting_ids:
                    message = await self._publish_turn_snapshot(
                        subscription=subscription,
                        table_id=table_id,
                        waiting_ids=waiting_ids,
                        player_names=current_player_names,
                        game_label=format_game_name(game_name),
                        signal_source=state.source,
                    )
                    if message is not None:
                        self._active_turn_messages[subscription.subscription_id] = ActiveTurnMessage(
                            message=message,
                            waiting_ids=list(waiting_ids),
                        )
                continue

            active_message = self._active_turn_messages.get(subscription.subscription_id)
            if active_message is None and waiting_ids:
                message = await self._publish_turn_snapshot(
                    subscription=subscription,
                    table_id=table_id,
                    waiting_ids=waiting_ids,
                    player_names=current_player_names,
                    game_label=format_game_name(game_name),
                    signal_source=state.source,
                )
                if message is not None:
                    self._active_turn_messages[subscription.subscription_id] = ActiveTurnMessage(
                        message=message,
                        waiting_ids=list(waiting_ids),
                    )
            elif waiting_ids != previous_waiting_ids:
                await self._handle_waiting_ids_transition(
                    subscription=subscription,
                    table_id=table_id,
                    previous_waiting_ids=previous_waiting_ids,
                    waiting_ids=waiting_ids,
                    player_names=current_player_names,
                    game_label=format_game_name(game_name),
                    signal_source=state.source,
                )

            self.database.update_watch_state(
                subscription_id=subscription.subscription_id,
                last_packet_id=table_packet_id,
                waiting_ids=waiting_ids,
                player_names=current_player_names,
                is_initialized=True,
                game_name=game_name,
            )

    async def _finalize_finished_table(
        self,
        subscriptions: list[WatchSubscription],
        table_id: str,
    ) -> None:
        for subscription in subscriptions:
            active_message = self._active_turn_messages.get(subscription.subscription_id)
            if active_message is not None:
                deleted = await self._delete_turn_message(
                    subscription=subscription,
                    active_message=active_message,
                    table_id=table_id,
                )
                if deleted:
                    self._active_turn_messages.pop(subscription.subscription_id, None)

            self.database.remove_watch_subscription(
                table_id=subscription.table_id,
                guild_id=subscription.guild_id,
                channel_id=subscription.channel_id,
            )

        self._table_tasks.pop(table_id, None)
        LOGGER.info(tr("table_finished_cleanup", table_id=table_id))

    async def _handle_waiting_ids_transition(
        self,
        *,
        subscription: WatchSubscription,
        table_id: str,
        previous_waiting_ids: list[str],
        waiting_ids: list[str],
        player_names: dict[str, str],
        game_label: str,
        signal_source: str,
    ) -> None:
        active_message = self._active_turn_messages.get(subscription.subscription_id)
        previous_set = set(previous_waiting_ids)
        waiting_set = set(waiting_ids)
        is_same_turn_progress = bool(previous_waiting_ids) and waiting_set.issubset(previous_set)

        if active_message is not None and not waiting_ids:
            deleted = await self._delete_turn_message(
                subscription=subscription,
                active_message=active_message,
                table_id=table_id,
            )
            if deleted:
                self._active_turn_messages.pop(subscription.subscription_id, None)
            return

        if active_message is not None and waiting_ids and is_same_turn_progress:
            edited = await self._edit_turn_message(
                subscription=subscription,
                active_message=active_message,
                table_id=table_id,
                waiting_ids=waiting_ids,
                player_names=player_names,
                game_label=game_label,
                signal_source=signal_source,
            )
            if edited:
                active_message.waiting_ids = list(waiting_ids)
                return

        if active_message is not None and waiting_ids and not is_same_turn_progress:
            deleted = await self._delete_turn_message(
                subscription=subscription,
                active_message=active_message,
                table_id=table_id,
            )
            if deleted:
                self._active_turn_messages.pop(subscription.subscription_id, None)

        if not waiting_ids:
            return

        message = await self._publish_turn_snapshot(
            subscription=subscription,
            table_id=table_id,
            waiting_ids=waiting_ids,
            player_names=player_names,
            game_label=game_label,
            signal_source=signal_source,
        )
        if message is not None:
            self._active_turn_messages[subscription.subscription_id] = ActiveTurnMessage(
                message=message,
                waiting_ids=list(waiting_ids),
            )

    async def _publish_turn_snapshot(
        self,
        *,
        subscription: WatchSubscription,
        table_id: str,
        waiting_ids: list[str],
        player_names: dict[str, str],
        game_label: str,
        signal_source: str
    ) -> discord.Message | None:
        channel = await self._resolve_channel(subscription, table_id)
        if channel is None:
            return None

        content = await self._build_turn_message_content(
            waiting_ids=waiting_ids,
            player_names=player_names,
            table_id=table_id,
            subscription=subscription,
            game_label=game_label,
            signal_source=signal_source
        )

        try:
            message = await channel.send(content)
            LOGGER.info(tr("notification_sent", table_id=table_id, waiting_ids=waiting_ids))
            return message
        except discord.DiscordException as exc:
            LOGGER.error(
                tr(
                    "notification_send_failed",
                    table_id=table_id,
                    channel_id=subscription.channel_id,
                    error=exc,
                )
            )
            return None

    async def _edit_turn_message(
        self,
        *,
        subscription: WatchSubscription,
        active_message: ActiveTurnMessage,
        table_id: str,
        waiting_ids: list[str],
        player_names: dict[str, str],
        game_label: str,
        signal_source: str,
    ) -> bool:
        channel = await self._resolve_channel(subscription, table_id)
        if channel is None or not isinstance(channel, discord.TextChannel):
            return False

        message = active_message.message

        content = await self._build_turn_message_content(
            waiting_ids=waiting_ids,
            player_names=player_names,
            table_id=table_id,
            subscription=subscription,
            game_label=game_label,
            signal_source=signal_source
        )
        try:
            await message.edit(content=content)
            LOGGER.info(tr("turn_message_updated", table_id=table_id, waiting_ids=waiting_ids))
            return True
        except discord.NotFound:
            LOGGER.info(tr("turn_message_missing_update", table_id=table_id))
            return False
        except discord.DiscordException as exc:
            LOGGER.error(tr("turn_message_update_failed", table_id=table_id, error=exc))
            return False

    async def _delete_turn_message(
        self,
        *,
        subscription: WatchSubscription,
        active_message: ActiveTurnMessage,
        table_id: str,
    ) -> bool:
        channel = await self._resolve_channel(subscription, table_id)
        if channel is None or not isinstance(channel, discord.TextChannel):
            return False

        message = active_message.message
        try:
            await message.delete()
            LOGGER.info(tr("turn_message_deleted", table_id=table_id))
            return True
        except discord.NotFound:
            LOGGER.info(tr("turn_message_missing_delete", table_id=table_id))
            return True
        except discord.DiscordException as exc:
            LOGGER.error(tr("turn_message_delete_failed", table_id=table_id, error=exc))
            return False

    async def _cleanup_stale_table_messages(
        self,
        subscriptions: list[WatchSubscription],
        table_id: str,
    ) -> None:
        if self.bot.user is None:
            return

        seen_channels: set[str] = set()
        deleted_count = 0
        table_markers = {f"{tr('label_table')} : {table_id}", f"{tr('label_table')}: {table_id}", f"Table : {table_id}", f"Table: {table_id}"}

        for subscription in subscriptions:
            if subscription.channel_id in seen_channels:
                continue
            seen_channels.add(subscription.channel_id)

            channel = await self._resolve_channel(subscription, table_id)
            if channel is None or not hasattr(channel, "history"):
                continue

            try:
                async for message in channel.history(limit=100):
                    if message.author.id != self.bot.user.id:
                        continue
                    if not any(marker in message.content for marker in table_markers):
                        continue
                    try:
                        await message.delete()
                        deleted_count += 1
                    except discord.NotFound:
                        continue
                    except discord.DiscordException as exc:
                        LOGGER.warning(
                            tr(
                                "stale_message_delete_failed",
                                table_id=table_id,
                                channel_id=subscription.channel_id,
                                error=exc,
                            )
                        )
            except discord.DiscordException as exc:
                LOGGER.warning(
                    tr(
                        "channel_history_cleanup_failed",
                        channel_id=subscription.channel_id,
                        table_id=table_id,
                        error=exc,
                    )
                )

        if deleted_count:
            LOGGER.info(tr("startup_cleanup", deleted_count=deleted_count, table_id=table_id))

    async def _build_turn_message_content(
        self,
        *,
        waiting_ids: list[str],
        player_names: dict[str, str],
        table_id: str,
        subscription: WatchSubscription,
        game_label: str,
        signal_source: str,
    ) -> str:
        observed_waiting_players = {
            player_id: player_names.get(player_id, "")
            for player_id in waiting_ids
        }
        linked_users = await asyncio.to_thread(
            self.database.get_linked_users_for_players,
            observed_waiting_players,
        )
        linked_users_by_bga_id = {user.bga_player_id: user for user in linked_users if user.bga_player_id}
        linked_users_by_name = {
            user.bga_player_name.casefold(): user
            for user in linked_users
            if user.bga_player_name
        }
        waiting_descriptions = ", ".join(
            self._format_waiting_player(
                player_id,
                player_names,
                linked_users_by_bga_id,
                linked_users_by_name,
            )
            for player_id in waiting_ids
        )

        return tr(
            "turn_message_content",
            game_label=tr("label_game"),
            game_name=game_label,
            table_label=tr("label_table"),
            table_id=table_id,
            players_label=tr("label_players_still_waiting"),
            players=waiting_descriptions or tr("value_none"),
            url_label=tr("label_url"),
            table_url=subscription.table_url or build_table_url(table_id),
        )

    async def _resolve_channel(self, subscription: WatchSubscription, table_id: str) -> discord.abc.Messageable | None:
        channel = self.bot.get_channel(int(subscription.channel_id))
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(int(subscription.channel_id))
            except discord.DiscordException as exc:
                LOGGER.error(
                    tr(
                        "channel_fetch_failed",
                        channel_id=subscription.channel_id,
                        table_id=table_id,
                        error=exc,
                    )
                )
                return None

        if not isinstance(channel, discord.abc.Messageable):
            LOGGER.error(
                tr(
                    "channel_not_messageable",
                    channel_id=subscription.channel_id,
                    table_id=table_id,
                )
            )
            return None
        return channel

    def _subscriptions_for_table(self, table_id: str) -> list[WatchSubscription]:
        return [item for item in self.database.list_watch_subscriptions() if item.table_id == table_id]

    @staticmethod
    def _format_player_reference(player_id: str, player_names: dict[str, str]) -> str:
        player_name = player_names.get(player_id)
        if player_name and player_name != player_id:
            return f"{player_name} ({player_id})"
        return player_id

    @classmethod
    def _format_waiting_player(
        cls,
        player_id: str,
        player_names: dict[str, str],
        linked_users_by_bga_id: dict[str, LinkedUser],
        linked_users_by_name: dict[str, LinkedUser],
    ) -> str:
        linked_user = linked_users_by_bga_id.get(player_id)
        if linked_user is None:
            player_name = player_names.get(player_id, "").strip()
            if player_name:
                linked_user = linked_users_by_name.get(player_name.casefold())
        if linked_user is None:
            return cls._format_player_reference(player_id, player_names)
        player_label = linked_user.bga_player_name or player_names.get(player_id, "").strip() or player_id
        player_id_label = linked_user.bga_player_id or player_id
        return f"<@{linked_user.discord_user_id}> {player_label} ({player_id_label})"

    @staticmethod
    def _select_previous_waiting_ids(subscriptions: list[WatchSubscription]) -> list[str]:
        initialized_subscriptions = [item for item in subscriptions if item.is_initialized]
        if not initialized_subscriptions:
            return []
        initialized_subscriptions.sort(key=lambda item: item.last_packet_id, reverse=True)
        return initialized_subscriptions[0].last_waiting_ids

    @staticmethod
    def _merge_player_names(subscriptions: list[WatchSubscription]) -> dict[str, str]:
        merged: dict[str, str] = {}
        for subscription in subscriptions:
            merged.update(subscription.player_names)
        return merged
