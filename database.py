from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from models import LinkedUser, WatchSubscription
from utils import json_dumps, json_loads_dict, json_loads_list, utc_now_iso


class Database:
    def __init__(self, db_path: Path, schema_path: Path) -> None:
        self.db_path = db_path
        self.schema_path = schema_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")

    def initialize(self) -> None:
        schema_sql = self.schema_path.read_text(encoding="utf-8")
        with self._lock:
            self._connection.executescript(schema_sql)
            self._ensure_watch_subscription_columns()
            self._ensure_watch_state_columns()
            self._migrate_legacy_watches_if_needed()
            self._drop_legacy_tables_if_safe()
            self._connection.commit()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def upsert_linked_user(
        self,
        discord_user_id: str,
        bga_player_id: str,
        bga_player_name: str,
    ) -> None:
        now = utc_now_iso()
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO users (
                    discord_user_id,
                    bga_player_id,
                    bga_player_name,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(discord_user_id) DO UPDATE SET
                    bga_player_id = excluded.bga_player_id,
                    bga_player_name = excluded.bga_player_name,
                    updated_at = excluded.updated_at
                """,
                (discord_user_id, bga_player_id, bga_player_name, now, now),
            )
            self._connection.commit()

    def get_linked_user(self, discord_user_id: str) -> LinkedUser | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT discord_user_id, bga_player_id, bga_player_name
                FROM users
                WHERE discord_user_id = ?
                """,
                (discord_user_id,),
            ).fetchone()
        if row is None:
            return None
        return LinkedUser(
            discord_user_id=row["discord_user_id"],
            bga_player_id=row["bga_player_id"],
            bga_player_name=row["bga_player_name"],
        )

    def remove_linked_user(self, discord_user_id: str) -> bool:
        with self._lock:
            cursor = self._connection.execute(
                "DELETE FROM users WHERE discord_user_id = ?",
                (discord_user_id,),
            )
            self._connection.commit()
            return cursor.rowcount > 0

    def list_linked_users(self) -> list[LinkedUser]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT discord_user_id, bga_player_id, bga_player_name
                FROM users
                ORDER BY bga_player_name COLLATE NOCASE, discord_user_id
                """
            ).fetchall()
        return [
            LinkedUser(
                discord_user_id=row["discord_user_id"],
                bga_player_id=row["bga_player_id"],
                bga_player_name=row["bga_player_name"],
            )
            for row in rows
        ]

    def get_linked_users_by_bga_ids(self, bga_player_ids: list[str]) -> list[LinkedUser]:
        if not bga_player_ids:
            return []
        placeholders = ",".join("?" for _ in bga_player_ids)
        with self._lock:
            rows = self._connection.execute(
                f"""
                SELECT discord_user_id, bga_player_id, bga_player_name
                FROM users
                WHERE bga_player_id IN ({placeholders})
                ORDER BY bga_player_name COLLATE NOCASE, discord_user_id
                """,
                tuple(bga_player_ids),
            ).fetchall()
        return [
            LinkedUser(
                discord_user_id=row["discord_user_id"],
                bga_player_id=row["bga_player_id"],
                bga_player_name=row["bga_player_name"],
            )
            for row in rows
        ]

    def upsert_watch_subscription(
        self,
        *,
        table_id: str,
        table_url: str,
        base_url: str,
        gameserver: str,
        guild_id: str,
        channel_id: str,
        created_by_discord_user_id: str,
        game_name: str | None,
    ) -> WatchSubscription:
        now = utc_now_iso()
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO watch_subscriptions (
                    table_id,
                    table_url,
                    base_url,
                    gameserver,
                    guild_id,
                    channel_id,
                    created_by_discord_user_id,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(table_id, guild_id, channel_id) DO UPDATE SET
                    table_url = excluded.table_url,
                    base_url = excluded.base_url,
                    gameserver = excluded.gameserver,
                    created_by_discord_user_id = excluded.created_by_discord_user_id,
                    updated_at = excluded.updated_at
                """,
                (
                    table_id,
                    table_url,
                    base_url,
                    gameserver,
                    guild_id,
                    channel_id,
                    created_by_discord_user_id,
                    now,
                    now,
                ),
            )
            row = self._connection.execute(
                """
                SELECT subscription_id
                FROM watch_subscriptions
                WHERE table_id = ? AND guild_id = ? AND channel_id = ?
                """,
                (table_id, guild_id, channel_id),
            ).fetchone()
            assert row is not None
            subscription_id = int(row["subscription_id"])
            self._connection.execute(
                """
                INSERT INTO watch_states (
                    subscription_id,
                    game_name,
                    updated_at
                ) VALUES (?, ?, ?)
                ON CONFLICT(subscription_id) DO UPDATE SET
                    game_name = COALESCE(excluded.game_name, watch_states.game_name),
                    updated_at = excluded.updated_at
                """,
                (subscription_id, game_name, now),
            )
            self._connection.commit()
        subscription = self.get_watch_subscription(subscription_id)
        assert subscription is not None
        return subscription

    def get_watch_subscription(self, subscription_id: int) -> WatchSubscription | None:
        with self._lock:
            row = self._connection.execute(self._watch_subscription_query() + " WHERE ws.subscription_id = ?", (subscription_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_watch_subscription(row)

    def remove_watch_subscription(self, *, table_id: str, guild_id: str, channel_id: str) -> bool:
        with self._lock:
            cursor = self._connection.execute(
                """
                DELETE FROM watch_subscriptions
                WHERE table_id = ? AND guild_id = ? AND channel_id = ?
                """,
                (table_id, guild_id, channel_id),
            )
            self._connection.commit()
            return cursor.rowcount > 0

    def remove_all_watch_subscriptions_for_guild(self, guild_id: str) -> int:
        with self._lock:
            cursor = self._connection.execute(
                "DELETE FROM watch_subscriptions WHERE guild_id = ?",
                (guild_id,),
            )
            self._connection.commit()
            return int(cursor.rowcount)

    def list_watch_subscriptions(self) -> list[WatchSubscription]:
        with self._lock:
            rows = self._connection.execute(
                self._watch_subscription_query() + " ORDER BY ws.table_id, ws.guild_id, ws.channel_id"
            ).fetchall()
        return [self._row_to_watch_subscription(row) for row in rows]

    def list_watch_subscriptions_for_guild(self, guild_id: str) -> list[WatchSubscription]:
        with self._lock:
            rows = self._connection.execute(
                self._watch_subscription_query() + " WHERE ws.guild_id = ? ORDER BY ws.table_id, ws.channel_id",
                (guild_id,),
            ).fetchall()
        return [self._row_to_watch_subscription(row) for row in rows]

    def update_watch_state(
        self,
        *,
        subscription_id: int,
        last_packet_id: int,
        waiting_ids: list[str],
        player_names: dict[str, str],
        is_initialized: bool,
        game_name: str | None,
    ) -> None:
        now = utc_now_iso()
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO watch_states (
                    subscription_id,
                    last_packet_id,
                    last_waiting_ids,
                    last_player_names,
                    is_initialized,
                    game_name,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(subscription_id) DO UPDATE SET
                    last_packet_id = excluded.last_packet_id,
                    last_waiting_ids = excluded.last_waiting_ids,
                    last_player_names = excluded.last_player_names,
                    is_initialized = excluded.is_initialized,
                    game_name = excluded.game_name,
                    updated_at = excluded.updated_at
                """,
                (
                    subscription_id,
                    last_packet_id,
                    json_dumps(waiting_ids),
                    json_dumps(player_names),
                    1 if is_initialized else 0,
                    game_name,
                    now,
                ),
            )
            self._connection.commit()

    def _ensure_watch_subscription_columns(self) -> None:
        existing_columns = self._column_names("watch_subscriptions")
        if "table_url" not in existing_columns:
            self._connection.execute("ALTER TABLE watch_subscriptions ADD COLUMN table_url TEXT")
        if "base_url" not in existing_columns:
            self._connection.execute("ALTER TABLE watch_subscriptions ADD COLUMN base_url TEXT")
        if "gameserver" not in existing_columns:
            self._connection.execute("ALTER TABLE watch_subscriptions ADD COLUMN gameserver TEXT")

    def _ensure_watch_state_columns(self) -> None:
        existing_columns = self._column_names("watch_states")
        if "last_player_names" not in existing_columns:
            self._connection.execute(
                "ALTER TABLE watch_states ADD COLUMN last_player_names TEXT NOT NULL DEFAULT '{}'"
            )

    def _migrate_legacy_watches_if_needed(self) -> None:
        if not self._table_exists("watches"):
            return
        if self._count_rows("watch_subscriptions") > 0:
            return

        now = utc_now_iso()
        self._connection.execute(
            """
            INSERT OR IGNORE INTO watch_subscriptions (
                table_id,
                guild_id,
                channel_id,
                created_by_discord_user_id,
                created_at,
                updated_at
            )
            SELECT
                table_id,
                guild_id,
                channel_id,
                MIN(discord_user_id) AS created_by_discord_user_id,
                MIN(created_at) AS created_at,
                MAX(updated_at) AS updated_at
            FROM watches
            GROUP BY table_id, guild_id, channel_id
            """
        )
        self._connection.execute(
            """
            INSERT OR IGNORE INTO watch_states (
                subscription_id,
                last_packet_id,
                last_waiting_ids,
                is_initialized,
                game_name,
                updated_at
            )
            SELECT
                ws.subscription_id,
                COALESCE(
                    (
                        SELECT MAX(COALESCE(w2.last_packet_id, 1))
                        FROM watches w2
                        WHERE w2.table_id = ws.table_id
                          AND w2.guild_id = ws.guild_id
                          AND w2.channel_id = ws.channel_id
                    ),
                    1
                ) AS last_packet_id,
                COALESCE(
                    (
                        SELECT w3.last_waiting_ids
                        FROM watches w3
                        WHERE w3.table_id = ws.table_id
                          AND w3.guild_id = ws.guild_id
                          AND w3.channel_id = ws.channel_id
                        ORDER BY COALESCE(w3.is_initialized, 0) DESC, COALESCE(w3.last_packet_id, 1) DESC
                        LIMIT 1
                    ),
                    '[]'
                ) AS last_waiting_ids,
                COALESCE(
                    (
                        SELECT MAX(COALESCE(w4.is_initialized, 0))
                        FROM watches w4
                        WHERE w4.table_id = ws.table_id
                          AND w4.guild_id = ws.guild_id
                          AND w4.channel_id = ws.channel_id
                    ),
                    0
                ) AS is_initialized,
                (
                    SELECT w5.game_name
                    FROM watches w5
                    WHERE w5.table_id = ws.table_id
                      AND w5.guild_id = ws.guild_id
                      AND w5.channel_id = ws.channel_id
                      AND w5.game_name IS NOT NULL
                    ORDER BY COALESCE(w5.updated_at, w5.created_at) DESC
                    LIMIT 1
                ) AS game_name,
                ? AS updated_at
            FROM watch_subscriptions ws
            """,
            (now,),
        )

    def _drop_legacy_tables_if_safe(self) -> None:
        if not self._table_exists("watches"):
            return
        if self._count_rows("watch_subscriptions") == 0:
            return
        self._connection.execute("DROP TABLE IF EXISTS watches")
        self._connection.execute("DROP INDEX IF EXISTS idx_watches_table_id")

    def _table_exists(self, table_name: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        return row is not None

    def _column_names(self, table_name: str) -> set[str]:
        rows = self._connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row[1]) for row in rows}

    def _count_rows(self, table_name: str) -> int:
        row = self._connection.execute(f"SELECT COUNT(*) AS count_value FROM {table_name}").fetchone()
        if row is None:
            return 0
        return int(row["count_value"])

    @staticmethod
    def _watch_subscription_query() -> str:
        return """
            SELECT
                ws.subscription_id,
                ws.table_id,
                ws.table_url,
                ws.base_url,
                ws.gameserver,
                ws.guild_id,
                ws.channel_id,
                ws.created_by_discord_user_id,
                COALESCE(st.last_packet_id, 1) AS last_packet_id,
                COALESCE(st.last_waiting_ids, '[]') AS last_waiting_ids,
                COALESCE(st.last_player_names, '{}') AS last_player_names,
                COALESCE(st.is_initialized, 0) AS is_initialized,
                st.game_name
            FROM watch_subscriptions ws
            LEFT JOIN watch_states st ON st.subscription_id = ws.subscription_id
        """

    @staticmethod
    def _row_to_watch_subscription(row: sqlite3.Row) -> WatchSubscription:
        return WatchSubscription(
            subscription_id=int(row["subscription_id"]),
            table_id=row["table_id"],
            table_url=row["table_url"],
            base_url=row["base_url"],
            gameserver=row["gameserver"],
            guild_id=row["guild_id"],
            channel_id=row["channel_id"],
            created_by_discord_user_id=row["created_by_discord_user_id"],
            last_packet_id=int(row["last_packet_id"]),
            last_waiting_ids=json_loads_list(row["last_waiting_ids"]),
            player_names=json_loads_dict(row["last_player_names"]),
            is_initialized=bool(row["is_initialized"]),
            game_name=row["game_name"],
        )
