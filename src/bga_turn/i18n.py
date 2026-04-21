from __future__ import annotations

import os


def get_bot_lang() -> str:
    candidate = os.getenv("BOT_LANG", "EN").strip().upper()
    if candidate in {"EN", "FR"}:
        return candidate
    return "EN"


_MESSAGES: dict[str, dict[str, str]] = {
    "command_group_description": {
        "EN": "Board Game Arena commands",
        "FR": "Commandes Board Game Arena",
    },
    "command_link_member_description": {
        "EN": "Manually link a Discord member to a BGA player",
        "FR": "Lie manuellement un membre Discord a un joueur BGA",
    },
    "command_link_member_member": {
        "EN": "Discord member to link",
        "FR": "Membre Discord a lier",
    },
    "command_link_member_name": {
        "EN": "BGA name used in notifications",
        "FR": "Nom BGA a afficher dans les notifications",
    },
    "command_link_member_id": {
        "EN": "BGA player ID",
        "FR": "ID joueur BGA",
    },
    "command_unlink_member_description": {
        "EN": "Remove the BGA link for a Discord member",
        "FR": "Supprime le lien BGA d'un membre Discord",
    },
    "command_unlink_member_member": {
        "EN": "Discord member to unlink",
        "FR": "Membre Discord a delier",
    },
    "command_linked_description": {
        "EN": "Show Discord members linked to BGA players",
        "FR": "Affiche les membres Discord lies a un joueur BGA",
    },
    "command_watch_description": {
        "EN": "Add a public BGA table to watch in this channel",
        "FR": "Ajoute une table BGA publique a surveiller dans ce salon",
    },
    "command_watch_target": {
        "EN": "Full public BGA table URL",
        "FR": "URL publique complete de la table BGA",
    },
    "command_unwatch_description": {
        "EN": "Remove a watched BGA table from this channel",
        "FR": "Retire une table BGA surveillee dans ce salon",
    },
    "command_unwatch_target": {
        "EN": "BGA table ID or full URL",
        "FR": "ID de table BGA ou URL complete",
    },
    "command_unwatch_all_description": {
        "EN": "Remove every BGA watch from the current server",
        "FR": "Supprime toutes les watches BGA du serveur courant",
    },
    "command_watchlist_description": {
        "EN": "Show watched tables for this server",
        "FR": "Affiche les tables surveillees sur ce serveur",
    },
    "command_status_description": {
        "EN": "Show the known state of watched tables on this server",
        "FR": "Affiche l'etat connu des tables surveillees sur ce serveur",
    },
    "error_manage_server_required_link": {
        "EN": "You need the `Manage Server` permission to link a Discord member to BGA.",
        "FR": "Il faut la permission `Manage Server` pour lier un membre Discord a un joueur BGA.",
    },
    "error_manage_server_required_unlink": {
        "EN": "You need the `Manage Server` permission to unlink a Discord member.",
        "FR": "Il faut la permission `Manage Server` pour delier un membre Discord.",
    },
    "error_manage_server_required_unwatch_all": {
        "EN": "You need the `Manage Server` permission to remove every watch from this server.",
        "FR": "Il faut la permission `Manage Server` pour supprimer toutes les watches du serveur.",
    },
    "error_need_bga_name_or_id": {
        "EN": "You must provide at least one `BgaName` or `BgaId` value.",
        "FR": "Il faut renseigner au moins un `NomBGA` ou un `IDBGA`.",
    },
    "error_invalid_bga_player_id": {
        "EN": "`bga_player_id` must be a valid numeric BGA player ID.",
        "FR": "`bga_player_id` doit etre un entier BGA valide.",
    },
    "error_command_server_channel_only": {
        "EN": "This command must be used in a Discord server channel.",
        "FR": "Cette commande doit etre lancee dans un salon de serveur Discord.",
    },
    "error_command_server_only": {
        "EN": "This command must be used in a Discord server.",
        "FR": "Cette commande doit etre lancee dans un serveur Discord.",
    },
    "error_watch_not_public": {
        "EN": "Table `{table_id}` is not usable in public/spectator mode: {error}",
        "FR": "La table `{table_id}` n'est pas exploitable en mode public/spectateur: {error}",
    },
    "error_watch_verify_failed": {
        "EN": "Could not verify table `{table_id}`: {error}",
        "FR": "Impossible de verifier la table `{table_id}`: {error}",
    },
    "link_saved": {
        "EN": "Link saved for {member_mention}.\nBGA name: `{bga_name}`\nBGA ID: `{bga_id}`",
        "FR": "Lien enregistre pour {member_mention}.\nNom BGA : `{bga_name}`\nBGA ID : `{bga_id}`",
    },
    "link_missing_value_placeholder": {
        "EN": "will be auto-completed",
        "FR": "sera complete automatiquement",
    },
    "unlink_not_found": {
        "EN": "No BGA link exists for {member_mention}.",
        "FR": "Aucun lien BGA n'existe pour {member_mention}.",
    },
    "unlink_saved": {
        "EN": "BGA link removed for {member_mention}.",
        "FR": "Lien BGA supprime pour {member_mention}.",
    },
    "linked_none": {
        "EN": "No Discord member is linked to BGA yet.",
        "FR": "Aucun membre Discord n'est encore lie a un joueur BGA.",
    },
    "linked_header": {
        "EN": "Known BGA links:",
        "FR": "Liens BGA connus :",
    },
    "linked_line": {
        "EN": "- <@{discord_user_id}> -> BgaName=`{bga_player_name}` | BgaId=`{bga_player_id}`",
        "FR": "- <@{discord_user_id}> -> NomBGA=`{bga_player_name}` | IDBGA=`{bga_player_id}`",
    },
    "watch_registered": {
        "EN": "Watch registered in zero-auth mode.\n{game_label}: `{game_name}`\n{table_label}: `{table_id}`\n{channel_label}: <#{channel_id}>\n{public_source_label}: `{source}`\n{players_detected_label}: {players}\n{url_label}: {table_url}\n{init_state_label}: {init_state}",
        "FR": "Watch enregistree en mode zero auth.\n{game_label} : `{game_name}`\n{table_label} : `{table_id}`\n{channel_label} : <#{channel_id}>\n{public_source_label} : `{source}`\n{players_detected_label} : {players}\n{url_label} : {table_url}\n{init_state_label} : {init_state}",
    },
    "watch_detected_none": {
        "EN": "no player detected yet",
        "FR": "aucun joueur detecte pour l'instant",
    },
    "watch_detected_more": {
        "EN": "(+{count} more)",
        "FR": "(+{count} autres)",
    },
    "watch_init_active": {
        "EN": "already active",
        "FR": "deja actif",
    },
    "watch_init_waiting_event": {
        "EN": "state will be published on the next public websocket event",
        "FR": "publication de l'etat au prochain evenement websocket public",
    },
    "unwatch_not_found": {
        "EN": "No active watch for table `{table_id}` in this channel.",
        "FR": "Aucune watch active pour la table `{table_id}` dans ce salon.",
    },
    "unwatch_removed": {
        "EN": "Watch removed for table `{table_id}` in this channel.",
        "FR": "Watch supprimee pour la table `{table_id}` dans ce salon.",
    },
    "unwatch_all_none": {
        "EN": "There is no BGA watch to remove on this server.",
        "FR": "Aucune watch BGA a supprimer sur ce serveur.",
    },
    "unwatch_all_removed": {
        "EN": "{removed_count} BGA watch(es) removed on this server.",
        "FR": "{removed_count} watch(es) BGA supprimee(s) sur ce serveur.",
    },
    "watchlist_none": {
        "EN": "No BGA table is watched on this server.",
        "FR": "Aucune table BGA n'est surveillee sur ce serveur.",
    },
    "watchlist_header": {
        "EN": "Watched tables:",
        "FR": "Tables surveillees :",
    },
    "watchlist_line": {
        "EN": "- Table `{table_id}` | {game_name}\n  {channel_label}: <#{channel_id}>\n  {state_label}: {state}\n  {url_label}: {table_url}",
        "FR": "- Table `{table_id}` | {game_name}\n  {channel_label} : <#{channel_id}>\n  {state_label} : {state}\n  {url_label} : {table_url}",
    },
    "watch_state_initialized": {
        "EN": "initialized",
        "FR": "initialise",
    },
    "watch_state_waiting_first_event": {
        "EN": "waiting for the first websocket event",
        "FR": "en attente du premier evenement websocket",
    },
    "status_none": {
        "EN": "No BGA table is watched on this server.",
        "FR": "Aucune table BGA n'est surveillee sur ce serveur.",
    },
    "status_header": {
        "EN": "Watch status:",
        "FR": "Etat des watches :",
    },
    "status_line": {
        "EN": "- Table `{table_id}` | {game_name}\n  {channel_label}: <#{channel_id}>\n  {waiting_ids_label}: `{waiting_ids}`\n  {state_label}: {state}",
        "FR": "- Table `{table_id}` | {game_name}\n  {channel_label} : <#{channel_id}>\n  {waiting_ids_label} : `{waiting_ids}`\n  {state_label} : {state}",
    },
    "status_unknown": {
        "EN": "unknown",
        "FR": "inconnu",
    },
    "status_waiting_for": {
        "EN": "waiting for {mentions}",
        "FR": "a jouer pour {mentions}",
    },
    "status_waiting_no_link": {
        "EN": "players are waiting, but no matching Discord link is known",
        "FR": "des joueurs sont attendus, mais aucun lien Discord correspondant n'est connu",
    },
    "status_no_waiting": {
        "EN": "no player waiting",
        "FR": "aucun joueur attendu",
    },
    "label_game": {
        "EN": "Game",
        "FR": "Jeu",
    },
    "label_table": {
        "EN": "Table",
        "FR": "Table",
    },
    "label_channel": {
        "EN": "Channel",
        "FR": "Salon",
    },
    "label_url": {
        "EN": "URL",
        "FR": "URL",
    },
    "label_state": {
        "EN": "State",
        "FR": "Etat",
    },
    "label_public_source_initial": {
        "EN": "Initial public source",
        "FR": "Source publique initiale",
    },
    "label_players_detected_currently": {
        "EN": "Currently detected players",
        "FR": "Joueurs detectes actuellement",
    },
    "label_init_state": {
        "EN": "Initialization state",
        "FR": "Etat d'initialisation",
    },
    "label_waiting_ids": {
        "EN": "Waiting IDs",
        "FR": "Waiting IDs",
    },
    "label_players_still_waiting": {
        "EN": "Players still waiting",
        "FR": "Joueurs encore attendus",
    },
    "value_none": {
        "EN": "none",
        "FR": "aucun",
    },
    "value_unknown": {
        "EN": "unknown",
        "FR": "inconnu",
    },
    "error_empty_table_value": {
        "EN": "The table value is empty.",
        "FR": "La valeur de table est vide.",
    },
    "error_invalid_table_id": {
        "EN": "Could not extract a valid BGA table ID.",
        "FR": "Impossible d'extraire un ID de table BGA valide.",
    },
    "error_empty_table_url": {
        "EN": "The BGA table URL is empty.",
        "FR": "L'URL de table BGA est vide.",
    },
    "error_watch_requires_full_public_url": {
        "EN": "The `/bga watch` command requires the full public BGA table URL.",
        "FR": "La commande `/bga watch` exige l'URL publique complete de la table BGA.",
    },
    "error_url_missing_table_param": {
        "EN": "The BGA URL does not contain a valid `table=<id>` parameter.",
        "FR": "L'URL BGA ne contient pas de parametre `table=<id>` valide.",
    },
    "error_url_missing_public_path": {
        "EN": "The BGA URL must contain the public game path, for example /15/sevenwondersdice?table=...",
        "FR": "L'URL BGA doit contenir le chemin public du jeu, par exemple /15/sevenwondersdice?table=...",
    },
    "error_url_missing_game_path": {
        "EN": "Could not extract the gameserver and game name from the BGA URL.",
        "FR": "Impossible d'extraire le gameserver et le nom du jeu depuis l'URL BGA.",
    },
    "error_load_tableinfos": {
        "EN": "Could not load tableinfos for table {table_id}: {error}",
        "FR": "Impossible de charger tableinfos pour la table {table_id}: {error}",
    },
    "error_tableinfos_http": {
        "EN": "Public tableinfos returned HTTP {status_code} for table {table_id}.",
        "FR": "tableinfos public renvoie HTTP {status_code} pour la table {table_id}.",
    },
    "error_tableinfos_invalid_json": {
        "EN": "Public tableinfos is not valid JSON for table {table_id}.",
        "FR": "tableinfos public n'est pas un JSON valide pour la table {table_id}.",
    },
    "error_tableinfos_unexpected": {
        "EN": "Unexpected public tableinfos payload for table {table_id}.",
        "FR": "tableinfos public inattendu pour la table {table_id}.",
    },
    "error_tableinfos_unexpected_payload": {
        "EN": "Unexpected public tableinfos payload for table {table_id}: status={status} exception={exception} error={error}",
        "FR": "Payload tableinfos public inattendu pour la table {table_id}: status={status} exception={exception} error={error}",
    },
    "error_tableinfos_missing_data": {
        "EN": "Public tableinfos does not contain a valid `data` block for table {table_id}.",
        "FR": "tableinfos public ne contient pas de bloc `data` valide pour la table {table_id}.",
    },
    "error_websocket_closed": {
        "EN": "Websocket connection closed: {error}",
        "FR": "Connexion websocket fermee: {error}",
    },
    "error_websocket_handshake_rejected": {
        "EN": "BGA websocket rejected the handshake for table {table_id}: HTTP {status_code} (likely a transient BGA/Cloudflare outage).",
        "FR": "BGA a rejete la poignee de main websocket pour la table {table_id} : HTTP {status_code} (probablement une coupure transitoire BGA/Cloudflare).",
    },
    "error_websocket_handshake_timeout": {
        "EN": "BGA websocket handshake timed out for table {table_id} on {websocket_url}.",
        "FR": "La poignee de main websocket BGA a expire pour la table {table_id} sur {websocket_url}.",
    },
    "error_load_public_page": {
        "EN": "Could not load public page {table_url}: {error}",
        "FR": "Impossible de charger la page publique {table_url}: {error}",
    },
    "error_public_page_http": {
        "EN": "The public page returned HTTP {status_code}.",
        "FR": "La page publique renvoie HTTP {status_code}.",
    },
    "error_missing_spectator_bootstrap": {
        "EN": "Could not extract the anonymous spectator identity from the public page.",
        "FR": "Impossible d'extraire l'identite spectateur anonyme depuis la page publique.",
    },
    "error_websocket_command_timeout": {
        "EN": "Timeout while waiting for websocket command {command_id}.",
        "FR": "Timeout sur la commande websocket {command_id}.",
    },
    "error_websocket_command_closed": {
        "EN": "Websocket closed while waiting for command {command_id}: {error}",
        "FR": "Connexion websocket fermee pendant la commande {command_id}: {error}",
    },
    "missing_discord_token": {
        "EN": "The DISCORD_TOKEN environment variable is required.",
        "FR": "La variable d'environnement DISCORD_TOKEN est obligatoire.",
    },
    "guild_sync": {
        "EN": "Slash commands synced for guild {guild_id} ({count} commands).",
        "FR": "Slash commands synchronisees sur la guilde {guild_id} ({count} commandes).",
    },
    "global_sync": {
        "EN": "Global slash commands synced ({count} commands).",
        "FR": "Slash commands globales synchronisees ({count} commandes).",
    },
    "global_cleanup_done": {
        "EN": "Deleted {count} stale global slash command(s) before guild sync.",
        "FR": "Suppression de {count} ancienne(s) slash command(s) globale(s) avant la sync guilde.",
    },
    "global_cleanup_skipped_no_guild": {
        "EN": "Skipping global slash command cleanup because DISCORD_GUILD_ID is not set.",
        "FR": "Nettoyage des slash commands globales ignore car DISCORD_GUILD_ID n'est pas renseigne.",
    },
    "tableinfos_status": {
        "EN": "Tableinfos {table_id} | status={status} | cancelled={cancelled} | time_end={time_end} | endgame_reason={endgame_reason} | finished={finished}",
        "FR": "Tableinfos {table_id} | status={status} | cancelled={cancelled} | time_end={time_end} | endgame_reason={endgame_reason} | finished={finished}",
    },
    "startup_tableinfos_check_failed": {
        "EN": "Initial tableinfos check failed for table {table_id}: {error}",
        "FR": "Le controle initial tableinfos a echoue pour la table {table_id}: {error}",
    },
    "idle_tableinfos_check_failed": {
        "EN": "Idle tableinfos check failed for table {table_id}: {error}",
        "FR": "Le controle tableinfos en periode d'inactivite a echoue pour la table {table_id}: {error}",
    },
    "error_table_redirected_to_lobby": {
        "EN": "BGA redirected the public page to the table lobby ({final_url}); the table is no longer spectable.",
        "FR": "BGA a redirige la page publique vers le lobby ({final_url}); la table n'est plus observable.",
    },
    "table_unavailable_autounwatch": {
        "EN": "Table {table_id} is no longer publicly spectable (likely finished or private): {error}. Auto-unwatching.",
        "FR": "Table {table_id} n'est plus observable publiquement (probablement terminee ou privee) : {error}. Desactivation automatique de la surveillance.",
    },
    "invalid_json_frame": {
        "EN": "Ignored BGA websocket frame because JSON is invalid: {line}",
        "FR": "Trame websocket BGA ignoree car JSON invalide: {line}",
    },
    "worker_stopped": {
        "EN": "Websocket worker stopped for table {table_id}.",
        "FR": "Worker websocket stoppe pour la table {table_id}.",
    },
    "worker_started": {
        "EN": "Websocket worker started for table {table_id}.",
        "FR": "Worker websocket demarre pour la table {table_id}.",
    },
    "legacy_watch_without_url": {
        "EN": "The watch for table {table_id} comes from an old configuration without a full public URL. Recreate it with /bga watch <url>.",
        "FR": "La watch de la table {table_id} vient d'une ancienne configuration sans URL publique complete. Recree-la avec /bga watch <url>.",
    },
    "table_not_public": {
        "EN": "Table {table_id} is not publicly usable: {error}",
        "FR": "Table {table_id} non exploitable publiquement: {error}",
    },
    "websocket_error": {
        "EN": "BGA websocket error on table {table_id}: {error}",
        "FR": "Erreur websocket BGA sur la table {table_id}: {error}",
    },
    "unexpected_worker_error": {
        "EN": "Unexpected error in websocket worker for table {table_id}.",
        "FR": "Erreur inattendue dans le worker websocket de la table {table_id}.",
    },
    "table_finished_public": {
        "EN": "Table {table_id} detected as finished by the public stream.",
        "FR": "Table {table_id} detectee comme terminee par le flux public.",
    },
    "table_state": {
        "EN": "Table {table_id} | packet={packet_id} | waiting_ids={waiting_ids} | source={source} | details={details}",
        "FR": "Table {table_id} | packet={packet_id} | waiting_ids={waiting_ids} | source={source} | details={details}",
    },
    "table_finished_cleanup": {
        "EN": "Watches automatically removed for finished table {table_id}.",
        "FR": "Watchs supprimees automatiquement pour la table terminee {table_id}.",
    },
    "player_name_refresh_success": {
        "EN": "Refreshed missing player names from the public page for table {table_id} ({count} resolved).",
        "FR": "Les noms manquants ont ete completes depuis la page publique pour la table {table_id} ({count} resolu(s)).",
    },
    "player_name_refresh_failed": {
        "EN": "Could not refresh player names from the public page for table {table_id}: {error}",
        "FR": "Impossible de rafraichir les noms des joueurs depuis la page publique pour la table {table_id}: {error}",
    },
    "notification_sent": {
        "EN": "Notification sent for table {table_id} for IDs {waiting_ids}.",
        "FR": "Notification envoyee sur la table {table_id} pour les IDs {waiting_ids}.",
    },
    "notification_send_failed": {
        "EN": "Failed to send Discord notification for table {table_id} to channel {channel_id}: {error}",
        "FR": "Echec d'envoi Discord pour la table {table_id} sur le salon {channel_id}: {error}",
    },
    "turn_message_updated": {
        "EN": "Turn message updated for table {table_id} (waiting_ids={waiting_ids}).",
        "FR": "Message de tour mis a jour pour la table {table_id} (waiting_ids={waiting_ids}).",
    },
    "turn_message_missing_update": {
        "EN": "Turn message already missing while updating table {table_id}.",
        "FR": "Message de tour deja introuvable pendant la mise a jour pour la table {table_id}.",
    },
    "turn_message_update_failed": {
        "EN": "Failed to update Discord message for table {table_id}: {error}",
        "FR": "Echec de mise a jour du message Discord pour la table {table_id}: {error}",
    },
    "turn_message_deleted": {
        "EN": "Turn message deleted for table {table_id}.",
        "FR": "Message de tour supprime pour la table {table_id}.",
    },
    "turn_message_missing_delete": {
        "EN": "Turn message already missing while deleting table {table_id}.",
        "FR": "Message de tour deja introuvable pendant la suppression pour la table {table_id}.",
    },
    "turn_message_delete_failed": {
        "EN": "Failed to delete Discord message for table {table_id}: {error}",
        "FR": "Echec de suppression du message Discord pour la table {table_id}: {error}",
    },
    "orphan_turn_message_deleted": {
        "EN": "Orphan turn message deleted for subscription {subscription_id}.",
        "FR": "Message de tour orphelin supprime pour la souscription {subscription_id}.",
    },
    "orphan_turn_message_delete_failed": {
        "EN": "Failed to delete orphan turn message for subscription {subscription_id}: {error}",
        "FR": "Echec de suppression du message de tour orphelin pour la souscription {subscription_id}: {error}",
    },
    "stale_message_delete_failed": {
        "EN": "Failed to delete an old message for table {table_id} in channel {channel_id}: {error}",
        "FR": "Impossible de supprimer un ancien message de la table {table_id} dans le salon {channel_id}: {error}",
    },
    "channel_history_cleanup_failed": {
        "EN": "Failed to browse history for channel {channel_id} while cleaning table {table_id}: {error}",
        "FR": "Impossible de parcourir l'historique du salon {channel_id} pour nettoyer la table {table_id}: {error}",
    },
    "startup_cleanup": {
        "EN": "Startup cleanup: deleted {deleted_count} old message(s) for table {table_id}.",
        "FR": "Nettoyage de demarrage: {deleted_count} ancien(s) message(s) supprime(s) pour la table {table_id}.",
    },
    "channel_fetch_failed": {
        "EN": "Failed to resolve channel {channel_id} for table {table_id}: {error}",
        "FR": "Impossible de recuperer le salon {channel_id} pour la table {table_id}: {error}",
    },
    "channel_not_messageable": {
        "EN": "Channel {channel_id} does not accept messages for table {table_id}.",
        "FR": "Le channel {channel_id} n'accepte pas les messages pour la table {table_id}.",
    },
    "turn_message_content": {
        "EN": "{game_label}: {game_name}\n{table_label}: {table_id}\n{players_label}: {players}\n{url_label}: {table_url}",
        "FR": "{game_label} : {game_name}\n{table_label} : {table_id}\n{players_label} : {players}\n{url_label} : {table_url}",
    },
}


def tr(key: str, **kwargs: object) -> str:
    templates = _MESSAGES.get(key)
    if templates is None:
        return key
    template = templates.get(get_bot_lang()) or templates["EN"]
    return template.format(**kwargs)
