from __future__ import annotations

import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from .bga_client import BgaClient, BgaClientError, BgaNotPublicError
from .database import Database
from .i18n import tr
from .monitor import BgaMonitor
from .utils import build_table_url, format_game_name, parse_public_table_url, parse_table_id


class BgaCommands(commands.Cog):
    bga = app_commands.Group(name="bga", description=tr("command_group_description"))

    def __init__(self, database: Database, bga_client: BgaClient, monitor: BgaMonitor) -> None:
        self.database = database
        self.bga_client = bga_client
        self.monitor = monitor

    @staticmethod
    def _has_manage_permissions(interaction: discord.Interaction) -> bool:
        permissions = interaction.permissions
        return permissions.manage_guild or permissions.administrator

    @staticmethod
    def _truncate_text(value: str, max_length: int) -> str:
        if max_length <= 0:
            return ""
        if len(value) <= max_length:
            return value
        if max_length == 1:
            return "…"
        return value[: max_length - 1].rstrip(", ") + "…"

    @classmethod
    def _format_bounded_list(cls, items: list[str], empty_text: str, max_length: int) -> str:
        if max_length <= 0:
            return ""
        if not items:
            return cls._truncate_text(empty_text, max_length)

        included: list[str] = []
        total_count = len(items)
        for index, item in enumerate(items):
            candidate_items = included + [item]
            candidate = ", ".join(candidate_items)
            remaining_count = total_count - index - 1
            if remaining_count > 0:
                suffix = tr("watch_detected_more", count=remaining_count)
                candidate = f"{candidate}, {suffix}"
            if len(candidate) <= max_length:
                included.append(item)
                continue
            if not included:
                return cls._truncate_text(item, max_length)
            break

        remaining_count = total_count - len(included)
        if remaining_count <= 0:
            return ", ".join(included)

        suffix = tr("watch_detected_more", count=remaining_count)
        while included:
            candidate = f'{", ".join(included)}, {suffix}'
            if len(candidate) <= max_length:
                return candidate
            included.pop()

        return cls._truncate_text(suffix, max_length)

    @classmethod
    def _split_message_lines(cls, header: str, lines: list[str], max_length: int = 2000) -> list[str]:
        current_chunk = cls._truncate_text(header, max_length)
        chunks: list[str] = []

        for line in lines:
            candidate = f"{current_chunk}\n{line}" if current_chunk else line
            if len(candidate) <= max_length:
                current_chunk = candidate
                continue

            if current_chunk:
                chunks.append(current_chunk)

            if len(line) <= max_length:
                current_chunk = line
            else:
                chunks.append(cls._truncate_text(line, max_length))
                current_chunk = ""

        if current_chunk:
            chunks.append(current_chunk)
        return chunks or [cls._truncate_text(header, max_length)]

    @staticmethod
    async def _send_ephemeral_chunks(
        interaction: discord.Interaction,
        chunks: list[str],
    ) -> None:
        if not chunks:
            chunks = [""]

        first_chunk, *remaining_chunks = chunks
        if interaction.response.is_done():
            await interaction.followup.send(first_chunk, ephemeral=True)
        else:
            await interaction.response.send_message(first_chunk, ephemeral=True)

        for chunk in remaining_chunks:
            await interaction.followup.send(chunk, ephemeral=True)

    @bga.command(name="link-member", description=tr("command_link_member_description"))
    @app_commands.describe(
        member=tr("command_link_member_member"),
        bga_player_name=tr("command_link_member_name"),
        bga_player_id=tr("command_link_member_id"),
    )
    async def link_member(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        bga_player_name: str | None = None,
        bga_player_id: str | None = None,
    ) -> None:
        if not self._has_manage_permissions(interaction):
            await interaction.response.send_message(
                tr("error_manage_server_required_link"),
                ephemeral=True,
            )
            return

        candidate_id = (bga_player_id or "").strip()
        candidate_name = (bga_player_name or "").strip()
        if not candidate_id and not candidate_name:
            await interaction.response.send_message(
                tr("error_need_bga_name_or_id"),
                ephemeral=True,
            )
            return
        if candidate_id and not candidate_id.isdigit():
            await interaction.response.send_message(
                tr("error_invalid_bga_player_id"),
                ephemeral=True,
            )
            return

        self.database.upsert_linked_user(
            discord_user_id=str(member.id),
            bga_player_id=candidate_id,
            bga_player_name=candidate_name,
        )
        linked_user = self.database.get_linked_user(str(member.id))
        if linked_user is None:
            raise RuntimeError("Failed to load the linked BGA user after saving it.")
        name_display = linked_user.bga_player_name or tr("link_missing_value_placeholder")
        id_display = linked_user.bga_player_id or tr("link_missing_value_placeholder")
        await interaction.response.send_message(
            tr(
                "link_saved",
                member_mention=member.mention,
                bga_name=name_display,
                bga_id=id_display,
            ),
            ephemeral=True,
        )

    @bga.command(name="unlink-member", description=tr("command_unlink_member_description"))
    @app_commands.describe(member=tr("command_unlink_member_member"))
    async def unlink_member(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> None:
        if not self._has_manage_permissions(interaction):
            await interaction.response.send_message(
                tr("error_manage_server_required_unlink"),
                ephemeral=True,
            )
            return

        removed = self.database.remove_linked_user(str(member.id))
        if not removed:
            await interaction.response.send_message(
                tr("unlink_not_found", member_mention=member.mention),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            tr("unlink_saved", member_mention=member.mention),
            ephemeral=True,
        )

    @bga.command(name="linked", description=tr("command_linked_description"))
    async def linked(self, interaction: discord.Interaction) -> None:
        linked_users = self.database.list_linked_users()
        if not linked_users:
            await interaction.response.send_message(
                tr("linked_none"),
                ephemeral=True,
            )
            return

        lines = [
            tr(
                "linked_line",
                discord_user_id=item.discord_user_id,
                bga_player_name=item.bga_player_name or tr("value_unknown"),
                bga_player_id=item.bga_player_id or tr("value_unknown"),
            )
            for item in linked_users
        ]
        await self._send_ephemeral_chunks(
            interaction,
            self._split_message_lines(tr("linked_header"), lines),
        )

    @bga.command(name="watch", description=tr("command_watch_description"))
    @app_commands.describe(table_or_url=tr("command_watch_target"))
    async def watch(self, interaction: discord.Interaction, table_or_url: str) -> None:
        if interaction.guild_id is None or interaction.channel_id is None:
            await interaction.response.send_message(
                tr("error_command_server_channel_only"),
                ephemeral=True,
            )
            return

        try:
            table_id, table_url, base_url, gameserver, game_name = parse_public_table_url(table_or_url)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        table_info = self.bga_client.build_public_table_info(
            table_id=table_id,
            table_url=table_url,
            base_url=base_url,
            gameserver=gameserver,
            game_name=game_name,
        )

        try:
            state = await self.bga_client.probe_public_table(table_info, known_player_names={})
        except BgaNotPublicError as exc:
            await interaction.followup.send(
                tr("error_watch_not_public", table_id=table_info.table_id, error=exc),
                ephemeral=True,
            )
            return
        except BgaClientError as exc:
            await interaction.followup.send(
                tr("error_watch_verify_failed", table_id=table_info.table_id, error=exc),
                ephemeral=True,
            )
            return

        subscription = self.database.upsert_watch_subscription(
            table_id=table_info.table_id,
            table_url=table_info.table_url,
            base_url=table_info.base_url,
            gameserver=table_info.gameserver,
            guild_id=str(interaction.guild_id),
            channel_id=str(interaction.channel_id),
            created_by_discord_user_id=str(interaction.user.id),
            game_name=table_info.game_name,
        )
        persisted_player_names = dict(subscription.player_names)
        persisted_player_names.update(state.player_names)
        self.database.update_watch_state(
            subscription_id=subscription.subscription_id,
            last_packet_id=subscription.last_packet_id,
            waiting_ids=subscription.last_waiting_ids,
            player_names=persisted_player_names,
            is_initialized=subscription.is_initialized,
            game_name=table_info.game_name,
        )
        await asyncio.to_thread(self.database.enrich_linked_users_from_players, persisted_player_names)
        linked_users = await asyncio.to_thread(self.database.get_linked_users_for_players, state.player_names)
        linked_by_bga_id = {item.bga_player_id: item for item in linked_users if item.bga_player_id}
        linked_by_name = {
            item.bga_player_name.casefold(): item
            for item in linked_users
            if item.bga_player_name
        }
        detected_players = []
        for player_id, player_name in sorted(state.player_names.items()):
            linked_user = linked_by_bga_id.get(player_id)
            if linked_user is None and player_name:
                linked_user = linked_by_name.get(player_name.casefold())
            if linked_user is not None:
                detected_players.append(
                    f"<@{linked_user.discord_user_id}> {player_name} ({player_id})"
                )
            else:
                detected_players.append(f"{player_name} ({player_id})")
        init_status = (
            tr("watch_init_active")
            if subscription.is_initialized
            else tr("watch_init_waiting_event")
        )
        message_kwargs = {
            "game_label": tr("label_game"),
            "game_name": format_game_name(table_info.game_name),
            "table_label": tr("label_table"),
            "table_id": table_info.table_id,
            "channel_label": tr("label_channel"),
            "channel_id": interaction.channel_id,
            "public_source_label": tr("label_public_source_initial"),
            "source": state.source,
            "players_detected_label": tr("label_players_detected_currently"),
            "url_label": tr("label_url"),
            "table_url": table_info.table_url,
            "init_state_label": tr("label_init_state"),
            "init_state": init_status,
        }
        message_overhead = len(tr("watch_registered", players="", **message_kwargs))
        max_players_length = max(0, 2000 - message_overhead)
        detected_players_text = self._format_bounded_list(
            detected_players,
            tr("watch_detected_none"),
            max_players_length,
        )
        message_content = tr(
            "watch_registered",
            players=detected_players_text,
            **message_kwargs,
        )

        await interaction.followup.send(message_content, ephemeral=True)
        await self.monitor.refresh_now()

    @bga.command(name="unwatch", description=tr("command_unwatch_description"))
    @app_commands.describe(table_or_url=tr("command_unwatch_target"))
    async def unwatch(self, interaction: discord.Interaction, table_or_url: str) -> None:
        if interaction.guild_id is None or interaction.channel_id is None:
            await interaction.response.send_message(
                tr("error_command_server_channel_only"),
                ephemeral=True,
            )
            return

        try:
            table_id = parse_table_id(table_or_url)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        removed = self.database.remove_watch_subscription(
            table_id=table_id,
            guild_id=str(interaction.guild_id),
            channel_id=str(interaction.channel_id),
        )
        if not removed:
            await interaction.response.send_message(
                tr("unwatch_not_found", table_id=table_id),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            tr("unwatch_removed", table_id=table_id),
            ephemeral=True,
        )
        await self.monitor.refresh_now()

    @bga.command(name="unwatch-all", description=tr("command_unwatch_all_description"))
    async def unwatch_all(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                tr("error_command_server_only"),
                ephemeral=True,
            )
            return

        if not self._has_manage_permissions(interaction):
            await interaction.response.send_message(
                tr("error_manage_server_required_unwatch_all"),
                ephemeral=True,
            )
            return

        removed_count = self.database.remove_all_watch_subscriptions_for_guild(str(interaction.guild_id))
        if removed_count == 0:
            await interaction.response.send_message(
                tr("unwatch_all_none"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            tr("unwatch_all_removed", removed_count=removed_count),
            ephemeral=True,
        )
        await self.monitor.refresh_now()

    @bga.command(name="watchlist", description=tr("command_watchlist_description"))
    async def watchlist(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                tr("error_command_server_only"),
                ephemeral=True,
            )
            return

        subscriptions = self.database.list_watch_subscriptions_for_guild(str(interaction.guild_id))
        if not subscriptions:
            await interaction.response.send_message(
                tr("watchlist_none"),
                ephemeral=True,
            )
            return

        lines = []
        for subscription in subscriptions:
            public_url = subscription.table_url or build_table_url(subscription.table_id)
            lines.append(
                tr(
                    "watchlist_line",
                    table_id=subscription.table_id,
                    game_name=format_game_name(subscription.game_name),
                    channel_label=tr("label_channel"),
                    channel_id=subscription.channel_id,
                    state_label=tr("label_state"),
                    state=(
                        tr("watch_state_initialized")
                        if subscription.is_initialized
                        else tr("watch_state_waiting_first_event")
                    ),
                    url_label=tr("label_url"),
                    table_url=public_url,
                )
            )

        await self._send_ephemeral_chunks(
            interaction,
            self._split_message_lines(tr("watchlist_header"), lines),
        )

    @bga.command(name="status", description=tr("command_status_description"))
    async def status(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                tr("error_command_server_only"),
                ephemeral=True,
            )
            return

        subscriptions = self.database.list_watch_subscriptions_for_guild(str(interaction.guild_id))
        if not subscriptions:
            await interaction.response.send_message(
                tr("status_none"),
                ephemeral=True,
            )
            return

        lines = []
        for subscription in subscriptions:
            if not subscription.is_initialized:
                state = tr("status_unknown")
            elif subscription.last_waiting_ids:
                linked_users = self.database.get_linked_users_by_bga_ids(subscription.last_waiting_ids)
                if linked_users:
                    mentions = ", ".join(f"<@{item.discord_user_id}>" for item in linked_users)
                    state = tr("status_waiting_for", mentions=mentions)
                else:
                    state = tr("status_waiting_no_link")
            else:
                state = tr("status_no_waiting")

            lines.append(
                tr(
                    "status_line",
                    table_id=subscription.table_id,
                    game_name=format_game_name(subscription.game_name),
                    channel_label=tr("label_channel"),
                    channel_id=subscription.channel_id,
                    waiting_ids_label=tr("label_waiting_ids"),
                    waiting_ids=", ".join(subscription.last_waiting_ids) or tr("value_none"),
                    state_label=tr("label_state"),
                    state=state,
                )
            )

        await self._send_ephemeral_chunks(
            interaction,
            self._split_message_lines(tr("status_header"), lines),
        )
