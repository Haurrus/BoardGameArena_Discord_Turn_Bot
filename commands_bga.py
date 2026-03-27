from __future__ import annotations

import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from bga_client import BgaClient, BgaClientError, BgaNotPublicError
from database import Database
from utils import build_table_url, format_game_name, parse_public_table_url, parse_table_id


class BgaCommands(commands.Cog):
    bga = app_commands.Group(name="bga", description="Commandes Board Game Arena")

    def __init__(self, database: Database, bga_client: BgaClient) -> None:
        self.database = database
        self.bga_client = bga_client

    @staticmethod
    def _has_manage_permissions(interaction: discord.Interaction) -> bool:
        permissions = interaction.permissions
        return permissions.manage_guild or permissions.administrator

    @bga.command(name="link-member", description="Lie manuellement un membre Discord a un ID BGA")
    @app_commands.describe(
        member="Membre Discord a lier",
        bga_player_id="ID joueur BGA",
        bga_player_name="Nom BGA a afficher dans les notifications",
    )
    async def link_member(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        bga_player_id: str,
        bga_player_name: str,
    ) -> None:
        if not self._has_manage_permissions(interaction):
            await interaction.response.send_message(
                "Il faut la permission `Manage Server` pour lier un membre Discord a un ID BGA.",
                ephemeral=True,
            )
            return

        candidate_id = bga_player_id.strip()
        candidate_name = bga_player_name.strip()
        if not candidate_id.isdigit():
            await interaction.response.send_message(
                "`bga_player_id` doit etre un entier BGA valide.",
                ephemeral=True,
            )
            return
        if not candidate_name:
            await interaction.response.send_message(
                "`bga_player_name` ne peut pas etre vide.",
                ephemeral=True,
            )
            return

        self.database.upsert_linked_user(
            discord_user_id=str(member.id),
            bga_player_id=candidate_id,
            bga_player_name=candidate_name,
        )
        await interaction.response.send_message(
            (
                f"Lien enregistre pour {member.mention}.\n"
                f"BGA ID : `{candidate_id}`\n"
                f"Nom BGA : `{candidate_name}`"
            ),
            ephemeral=True,
        )

    @bga.command(name="unlink-member", description="Supprime le lien BGA d'un membre Discord")
    @app_commands.describe(member="Membre Discord a delier")
    async def unlink_member(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> None:
        if not self._has_manage_permissions(interaction):
            await interaction.response.send_message(
                "Il faut la permission `Manage Server` pour delier un membre Discord.",
                ephemeral=True,
            )
            return

        removed = self.database.remove_linked_user(str(member.id))
        if not removed:
            await interaction.response.send_message(
                f"Aucun lien BGA n'existe pour {member.mention}.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Lien BGA supprime pour {member.mention}.",
            ephemeral=True,
        )

    @bga.command(name="linked", description="Affiche les membres Discord lies a un ID BGA")
    async def linked(self, interaction: discord.Interaction) -> None:
        linked_users = self.database.list_linked_users()
        if not linked_users:
            await interaction.response.send_message(
                "Aucun membre Discord n'est encore lie a un ID BGA.",
                ephemeral=True,
            )
            return

        lines = [
            f"- <@{item.discord_user_id}> -> `{item.bga_player_name}` (`{item.bga_player_id}`)"
            for item in linked_users
        ]
        await interaction.response.send_message(
            "Liens BGA connus :\n" + "\n".join(lines),
            ephemeral=True,
        )

    @bga.command(name="watch", description="Ajoute une table BGA publique a surveiller dans ce salon")
    @app_commands.describe(table_or_url="URL complete publique de table BGA")
    async def watch(self, interaction: discord.Interaction, table_or_url: str) -> None:
        if interaction.guild_id is None or interaction.channel_id is None:
            await interaction.response.send_message(
                "Cette commande doit etre lancee dans un salon de serveur Discord.",
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
                f"La table `{table_id}` n'est pas exploitable en mode public/spectateur: {exc}",
                ephemeral=True,
            )
            return
        except BgaClientError as exc:
            await interaction.followup.send(
                f"Impossible de verifier la table `{table_id}`: {exc}",
                ephemeral=True,
            )
            return

        subscription = self.database.upsert_watch_subscription(
            table_id=table_id,
            table_url=table_url,
            base_url=base_url,
            gameserver=gameserver,
            guild_id=str(interaction.guild_id),
            channel_id=str(interaction.channel_id),
            created_by_discord_user_id=str(interaction.user.id),
            game_name=game_name,
        )
        linked_users = self.database.get_linked_users_by_bga_ids(list(state.player_names.keys()))
        linked_mentions = ", ".join(f"<@{item.discord_user_id}>" for item in linked_users)
        if not linked_mentions:
            linked_mentions = "aucun joueur lie pour l'instant"
        init_status = (
            "deja actif"
            if subscription.is_initialized
            else "publication de l'etat au prochain evenement websocket public"
        )

        await interaction.followup.send(
            (
                "Watch enregistree en mode zero auth.\n"
                f"Jeu : `{format_game_name(game_name)}`\n"
                f"Table : `{table_id}`\n"
                f"Salon : <#{interaction.channel_id}>\n"
                f"Source publique initiale : `{state.source}`\n"
                f"Joueurs lies actuellement detectes : {linked_mentions}\n"
                f"URL : {table_url}\n"
                f"Etat d'initialisation : {init_status}"
            ),
            ephemeral=True,
        )

    @bga.command(name="unwatch", description="Retire une table BGA surveillee dans ce salon")
    @app_commands.describe(table_or_url="ID de table BGA ou URL complete")
    async def unwatch(self, interaction: discord.Interaction, table_or_url: str) -> None:
        if interaction.guild_id is None or interaction.channel_id is None:
            await interaction.response.send_message(
                "Cette commande doit etre lancee dans un salon de serveur Discord.",
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
                f"Aucune watch active pour la table `{table_id}` dans ce salon.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Watch supprimee pour la table `{table_id}` dans ce salon.",
            ephemeral=True,
        )

    @bga.command(name="unwatch-all", description="Supprime toutes les watches BGA du serveur courant")
    async def unwatch_all(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "Cette commande doit etre lancee dans un serveur Discord.",
                ephemeral=True,
            )
            return

        if not self._has_manage_permissions(interaction):
            await interaction.response.send_message(
                "Il faut la permission `Manage Server` pour supprimer toutes les watches du serveur.",
                ephemeral=True,
            )
            return

        removed_count = self.database.remove_all_watch_subscriptions_for_guild(str(interaction.guild_id))
        if removed_count == 0:
            await interaction.response.send_message(
                "Aucune watch BGA a supprimer sur ce serveur.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"{removed_count} watch(es) BGA supprimee(s) sur ce serveur.",
            ephemeral=True,
        )

    @bga.command(name="watchlist", description="Affiche les tables surveillees sur ce serveur")
    async def watchlist(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "Cette commande doit etre lancee dans un serveur Discord.",
                ephemeral=True,
            )
            return

        subscriptions = self.database.list_watch_subscriptions_for_guild(str(interaction.guild_id))
        if not subscriptions:
            await interaction.response.send_message(
                "Aucune table BGA n'est surveillee sur ce serveur.",
                ephemeral=True,
            )
            return

        lines = []
        for subscription in subscriptions:
            public_url = subscription.table_url or build_table_url(subscription.table_id)
            lines.append(
                (
                    f"- Table `{subscription.table_id}` | {format_game_name(subscription.game_name)}\n"
                    f"  Salon : <#{subscription.channel_id}>\n"
                    f"  Etat : {'initialise' if subscription.is_initialized else 'en attente du premier evenement websocket'}\n"
                    f"  URL : {public_url}"
                )
            )

        await interaction.response.send_message(
            "Tables surveillees :\n" + "\n".join(lines),
            ephemeral=True,
        )

    @bga.command(name="status", description="Affiche l'etat connu des tables surveillees sur ce serveur")
    async def status(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "Cette commande doit etre lancee dans un serveur Discord.",
                ephemeral=True,
            )
            return

        subscriptions = self.database.list_watch_subscriptions_for_guild(str(interaction.guild_id))
        if not subscriptions:
            await interaction.response.send_message(
                "Aucune table BGA n'est surveillee sur ce serveur.",
                ephemeral=True,
            )
            return

        lines = []
        for subscription in subscriptions:
            if not subscription.is_initialized:
                state = "inconnu"
            elif subscription.last_waiting_ids:
                linked_users = self.database.get_linked_users_by_bga_ids(subscription.last_waiting_ids)
                if linked_users:
                    mentions = ", ".join(f"<@{item.discord_user_id}>" for item in linked_users)
                    state = f"a jouer pour {mentions}"
                else:
                    state = "des joueurs sont attendus, mais aucun lien Discord correspondant n'est connu"
            else:
                state = "aucun joueur attendu"

            lines.append(
                (
                    f"- Table `{subscription.table_id}` | {format_game_name(subscription.game_name)}\n"
                    f"  Salon : <#{subscription.channel_id}>\n"
                    f"  Waiting IDs : `{', '.join(subscription.last_waiting_ids) or 'aucun'}`\n"
                    f"  Etat : {state}"
                )
            )

        await interaction.response.send_message(
            "Etat des watches :\n" + "\n".join(lines),
            ephemeral=True,
        )
