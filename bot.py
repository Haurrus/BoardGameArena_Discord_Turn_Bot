from __future__ import annotations

import logging
import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=ROOT_DIR / ".env", encoding="utf-8-sig")

from bga_client import BgaClient
from commands_bga import BgaCommands
from database import Database
from i18n import tr
from monitor import BgaMonitor


def setup_logging() -> None:
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


class BgaDiscordBot(commands.Bot):
    def __init__(
        self,
        *,
        database: Database,
        bga_client: BgaClient,
        poll_seconds: int,
        dev_guild_id: int | None,
    ) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.database = database
        self.bga_client = bga_client
        self.dev_guild_id = dev_guild_id
        self.monitor = BgaMonitor(self, database, bga_client, poll_seconds)
        self.logger = logging.getLogger(__name__)
        self._startup_completed = False

    async def setup_hook(self) -> None:
        await self.add_cog(BgaCommands(self.database, self.bga_client, self.monitor))

    async def on_ready(self) -> None:
        if self._startup_completed:
            return

        if self.dev_guild_id is not None:
            guild = discord.Object(id=self.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            self.logger.info(tr("guild_sync", guild_id=self.dev_guild_id, count=len(synced)))
        else:
            synced = await self.tree.sync()
            self.logger.info(tr("global_sync", count=len(synced)))

        self.monitor.start()
        self._startup_completed = True

    async def close(self) -> None:
        self.monitor.stop()
        self.database.close()
        await super().close()


def main() -> None:
    setup_logging()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError(tr("missing_discord_token"))

    db_path = Path(os.getenv("BGA_DB_PATH", ROOT_DIR / "bga_bot.db"))
    schema_path = ROOT_DIR / "schema.sql"
    poll_seconds = int(os.getenv("BGA_POLL_SECONDS", "15"))
    dev_guild_id = os.getenv("DISCORD_GUILD_ID")
    websocket_url = os.getenv("BGA_WS_URL", "wss://ws-x1.boardgamearena.com/connection/websocket")

    database = Database(db_path=db_path, schema_path=schema_path)
    database.initialize()
    bga_client = BgaClient(timeout=30, websocket_url=websocket_url)

    bot = BgaDiscordBot(
        database=database,
        bga_client=bga_client,
        poll_seconds=poll_seconds,
        dev_guild_id=int(dev_guild_id) if dev_guild_id else None,
    )
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
