from __future__ import annotations

import logging
import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from bga_client import BgaClient
from commands_bga import BgaCommands
from database import Database
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
            self.logger.info(
                "Slash commands synchronisees sur la guilde %s (%s commandes).",
                self.dev_guild_id,
                len(synced),
            )
        else:
            synced = await self.tree.sync()
            self.logger.info("Slash commands globales synchronisees (%s commandes).", len(synced))

        self.monitor.start()
        self._startup_completed = True

    async def close(self) -> None:
        self.monitor.stop()
        self.database.close()
        await super().close()


def main() -> None:
    root_dir = Path(__file__).resolve().parent
    load_dotenv(dotenv_path=root_dir / ".env", encoding="utf-8-sig")
    setup_logging()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("La variable d'environnement DISCORD_TOKEN est obligatoire.")

    db_path = Path(os.getenv("BGA_DB_PATH", root_dir / "bga_bot.db"))
    schema_path = root_dir / "schema.sql"
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
