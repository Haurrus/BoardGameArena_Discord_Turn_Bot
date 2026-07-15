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
    "command_help_description": {
        "EN": "Show what the bot does and how to use it",
        "FR": "Explique ce que fait le bot et comment l'utiliser",
    },
    "help_header": {
        "EN": "╔═══════════════════════════════╗\nBGA BOT — HELP\n╚═══════════════════════════════╝",
        "FR": "╔═══════════════════════════════╗\nBOT BGA — AIDE\n╚═══════════════════════════════╝",
    },
    "help_section_intro": {
        "EN": (
            "・ WHAT THIS BOT DOES\n"
            "It spectates public Board Game Arena tables and posts a message when someone has to play.\n"
            "No BGA account, no password, no cookie: it only reads what any anonymous spectator can see.\n"
            "The message is updated as the turn moves on, and removed once nobody is waiting."
        ),
        "FR": (
            "・ CE QUE FAIT CE BOT\n"
            "Il observe des tables Board Game Arena publiques en mode spectateur et publie un message quand quelqu'un doit jouer.\n"
            "Aucun compte BGA, aucun mot de passe, aucun cookie : il ne lit que ce qu'un spectateur anonyme peut voir.\n"
            "Le message est mis a jour au fil du tour, puis retire quand plus personne n'est attendu."
        ),
    },
    "help_section_watch": {
        "EN": (
            "・ WATCH A TABLE\n"
            "The bot follows the game and notifies when it's someone's turn to play.\n"
            "/bga watch <table_link>\n"
            "Example ▸ /bga watch https://boardgamearena.com/6/perfectwords?table=827318521\n"
            "Copy the full table URL from your browser. A tableview link or the bare table id works too."
        ),
        "FR": (
            "・ SURVEILLER UNE TABLE\n"
            "Le bot suit la partie et notifie quand c'est au tour de quelqu'un de jouer.\n"
            "/bga watch <lien_de_la_table>\n"
            "Exemple ▸ /bga watch https://boardgamearena.com/6/perfectwords?table=827318521\n"
            "Copie l'URL complete de la table depuis ton navigateur. Un lien tableview ou l'id seul marchent aussi."
        ),
    },
    "help_section_follow": {
        "EN": (
            "・ FOLLOW A PLAYER — ON / OFF\n"
            "Watch every table a member plays on, automatically, instead of adding them one by one.\n"
            "/bga follow-tables @nickname\n"
            "Example ▸ /bga follow-tables @Haurrus\n"
            "Run it once to turn it ON, run it again to turn it OFF: the reply always tells you which state you are in.\n"
            "New tables are picked up on their own within 5 minutes. The member must be linked and have a BGA ID."
        ),
        "FR": (
            "・ SUIVRE UN JOUEUR — ON / OFF\n"
            "Surveille automatiquement toutes les tables d'un membre, au lieu de les ajouter une par une.\n"
            "/bga follow-tables @pseudo\n"
            "Exemple ▸ /bga follow-tables @Haurrus\n"
            "Lance-la une fois pour ACTIVER, relance-la pour DESACTIVER : la reponse indique toujours l'etat courant.\n"
            "Les nouvelles tables sont prises en compte toutes seules sous 5 minutes. Le membre doit etre lie et avoir un ID BGA."
        ),
    },
    "help_section_link": {
        "EN": (
            "・ ADD A PLAYER\n"
            "Link a Discord member to their Board Game Arena account.\n"
            "/bga link-member @nickname BGAName\n"
            "Example ▸ /bga link-member @Haurrus Haurrus\n"
            "The bot fills in the rest on its own as soon as it sees the person play.\n"
            "You can also give the numeric ID directly ▸ /bga link-member @Haurrus Haurrus 91713763"
        ),
        "FR": (
            "・ AJOUTER UN JOUEUR\n"
            "Lie un membre Discord a son compte Board Game Arena.\n"
            "/bga link-member @pseudo NomBGA\n"
            "Exemple ▸ /bga link-member @Haurrus Haurrus\n"
            "Le bot complete le reste tout seul des qu'il voit la personne jouer.\n"
            "Tu peux aussi donner l'ID numerique directement ▸ /bga link-member @Haurrus Haurrus 91713763"
        ),
    },
    "help_section_other": {
        "EN": (
            "・ OTHER COMMANDS\n"
            "/bga watchlist → lists watched tables\n"
            "/bga status → state of tracked games\n"
            "/bga linked → lists linked members\n"
            "/bga unwatch → stops watching a table\n"
            "/bga unwatch-all → stops all watches\n"
            "/bga unlink-member → removes a member's link"
        ),
        "FR": (
            "・ AUTRES COMMANDES\n"
            "/bga watchlist → liste les tables surveillees\n"
            "/bga status → etat des parties suivies\n"
            "/bga linked → liste les membres lies\n"
            "/bga unwatch → arrete de surveiller une table\n"
            "/bga unwatch-all → arrete toutes les surveillances\n"
            "/bga unlink-member → supprime le lien d'un membre"
        ),
    },
    "help_section_permissions": {
        "EN": (
            "・ PERMISSIONS\n"
            "Don't forget to give the bot the right permissions in the channel where you want it to work:\n"
            "▸ View Channels\n"
            "▸ Send Messages\n"
            "▸ Embed Links\n"
            "▸ Read Message History\n"
            "Linking, unlinking and /bga unwatch-all also need the `Manage Server` permission."
        ),
        "FR": (
            "・ PERMISSIONS\n"
            "N'oublie pas de donner au bot les bonnes permissions dans le salon ou tu veux qu'il travaille :\n"
            "▸ View Channels\n"
            "▸ Send Messages\n"
            "▸ Embed Links\n"
            "▸ Read Message History\n"
            "Lier, delier et /bga unwatch-all demandent en plus la permission `Manage Server`."
        ),
    },
    "help_footer": {
        "EN": (
            "The bot automatically stops watching a table when the game is over.\n"
            "Links and watches are specific to this server."
        ),
        "FR": (
            "Le bot arrete automatiquement de surveiller une table quand la partie est terminee.\n"
            "Les liens et les surveillances sont propres a ce serveur."
        ),
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
        "EN": "BGA table URL (game link, tableview link) or table id",
        "FR": "URL de table BGA (lien de jeu, lien tableview) ou identifiant de table",
    },
    "command_follow_tables_description": {
        "EN": "Toggle automatic watching of a member's BGA tables in this channel",
        "FR": "Active/desactive le suivi auto des tables BGA d'un membre dans ce salon",
    },
    "command_follow_tables_member": {
        "EN": "Discord member whose BGA tables should be followed",
        "FR": "Membre Discord dont les tables BGA doivent etre suivies",
    },
    "error_follow_member_not_linked": {
        "EN": "{member_mention} is not linked to any BGA player on this server. Link them first with `/bga link-member`.",
        "FR": "{member_mention} n'est lie a aucun joueur BGA sur ce serveur. Lie-le d'abord avec `/bga link-member`.",
    },
    "error_follow_member_without_id": {
        "EN": "{member_mention} is linked to the BGA name `{bga_name}` but has no BGA ID yet, and the ID is required to list their tables.\nEither set it with `/bga link-member member bga_player_id:<id>`, or wait for the bot to auto-complete it the next time they show up on a watched table.",
        "FR": "{member_mention} est lie au nom BGA `{bga_name}` mais n'a pas encore d'ID BGA, or l'ID est indispensable pour lister ses tables.\nRenseigne-le avec `/bga link-member membre bga_player_id:<id>`, ou attends que le bot le complete automatiquement lors de sa prochaine apparition sur une table surveillee.",
    },
    "error_follow_unknown_player": {
        "EN": "BGA does not know any player with ID `{bga_player_id}` (linked to {member_mention}). Fix the link with `/bga link-member`.",
        "FR": "BGA ne connait aucun joueur avec l'ID `{bga_player_id}` (lie a {member_mention}). Corrige le lien avec `/bga link-member`.",
    },
    "error_follow_lookup_failed": {
        "EN": "Could not list the BGA tables of {member_mention}: {error}",
        "FR": "Impossible de lister les tables BGA de {member_mention}: {error}",
    },
    "follow_tables_enabled": {
        "EN": "Automatic follow **enabled** for {member_mention} (`{bga_name}` / `{bga_id}`) in <#{channel_id}>.",
        "FR": "Suivi automatique **ACTIVE** pour {member_mention} (`{bga_name}` / `{bga_id}`) dans <#{channel_id}>.",
    },
    "follow_tables_disabled": {
        "EN": "Automatic follow **disabled** for {member_mention} in <#{channel_id}>.\nTables already watched stay watched; remove them with `/bga unwatch` or `/bga unwatch-all`.",
        "FR": "Suivi automatique **DESACTIVE** pour {member_mention} dans <#{channel_id}>.\nLes tables deja surveillees le restent ; retire-les avec `/bga unwatch` ou `/bga unwatch-all`.",
    },
    "follow_tables_added_header": {
        "EN": "Newly watched tables ({count}):",
        "FR": "Tables nouvellement surveillees ({count}) :",
    },
    "follow_tables_added_line": {
        "EN": "- `{table_id}` | {game_name}",
        "FR": "- `{table_id}` | {game_name}",
    },
    "follow_tables_added_none": {
        "EN": "No new table to watch: the player has no ongoing table, or they are all already watched in this channel.",
        "FR": "Aucune nouvelle table a surveiller : le joueur n'a aucune table en cours, ou elles sont deja toutes surveillees dans ce salon.",
    },
    "follow_tables_already_watched": {
        "EN": "Already watched here ({count}): {table_ids}",
        "FR": "Deja surveillees ici ({count}) : {table_ids}",
    },
    "follow_tables_toggle_hint": {
        "EN": "New tables are picked up automatically. Run `/bga follow-tables` again on this member to disable.",
        "FR": "Les nouvelles tables seront prises en compte automatiquement. Relance `/bga follow-tables` sur ce membre pour desactiver.",
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
    "error_resolve_missing_request_token": {
        "EN": "Could not obtain the anonymous request token from the tableview page for table {table_id}.",
        "FR": "Impossible d'obtenir le jeton de requete anonyme depuis la page tableview pour la table {table_id}.",
    },
    "error_resolve_missing_game_server": {
        "EN": "Could not resolve the game server for table {table_id} (it may be private, finished, or not started yet).",
        "FR": "Impossible de resoudre le serveur de jeu pour la table {table_id} (elle est peut-etre privee, terminee ou pas encore commencee).",
    },
    "resolved_public_table": {
        "EN": "Resolved table {table_id} to /{gameserver}/{game_name}.",
        "FR": "Table {table_id} resolue vers /{gameserver}/{game_name}.",
    },
    "roster_fetch_failed": {
        "EN": "Could not fetch the authoritative player roster for table {table_id}: {error}. Falling back to page extraction.",
        "FR": "Impossible de recuperer le roster autoritaire des joueurs pour la table {table_id}: {error}. Repli sur l'extraction depuis la page.",
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
    "player_tables_resolved": {
        "EN": "Player {player_id} currently sits at {count} watchable table(s).",
        "FR": "Le joueur {player_id} est actuellement sur {count} table(s) surveillable(s).",
    },
    "error_player_tables_missing_request_token": {
        "EN": "Could not obtain the anonymous request token from the playertables page for player {player_id}.",
        "FR": "Impossible d'obtenir le jeton de requete anonyme depuis la page playertables pour le joueur {player_id}.",
    },
    "error_load_player_tables": {
        "EN": "Could not load the table list for player {player_id}: {error}",
        "FR": "Impossible de charger la liste des tables du joueur {player_id}: {error}",
    },
    "error_player_tables_http": {
        "EN": "The player table list returned HTTP {status_code} for player {player_id}.",
        "FR": "La liste des tables renvoie HTTP {status_code} pour le joueur {player_id}.",
    },
    "error_player_tables_invalid_json": {
        "EN": "The player table list is not valid JSON for player {player_id}.",
        "FR": "La liste des tables n'est pas un JSON valide pour le joueur {player_id}.",
    },
    "error_player_tables_unexpected_payload": {
        "EN": "Unexpected player table list payload for player {player_id}: status={status} error={error}",
        "FR": "Payload inattendu de la liste des tables pour le joueur {player_id}: status={status} error={error}",
    },
    "error_player_tables_missing_data": {
        "EN": "The player table list does not contain a valid `data` block for player {player_id}.",
        "FR": "La liste des tables ne contient pas de bloc `data` valide pour le joueur {player_id}.",
    },
    "error_player_tables_unknown_player": {
        "EN": "BGA does not know any player with ID {player_id}.",
        "FR": "BGA ne connait aucun joueur avec l'ID {player_id}.",
    },
    "follow_sync_skipped_without_id": {
        "EN": "Follow sync skipped for Discord user {discord_user_id}: no BGA ID is linked anymore.",
        "FR": "Sync du suivi ignoree pour l'utilisateur Discord {discord_user_id}: plus aucun ID BGA n'est lie.",
    },
    "follow_sync_failed": {
        "EN": "Follow sync failed for Discord user {discord_user_id} (BGA {bga_player_id}): {error}",
        "FR": "Sync du suivi echouee pour l'utilisateur Discord {discord_user_id} (BGA {bga_player_id}): {error}",
    },
    "follow_sync_added": {
        "EN": "Follow sync watched {count} new table(s) for BGA {bga_player_id} in channel {channel_id}: {table_ids}",
        "FR": "La sync du suivi a ajoute {count} nouvelle(s) table(s) pour BGA {bga_player_id} dans le salon {channel_id}: {table_ids}",
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
    "command_invocation": {
        "EN": "Slash command /{command} invoked by {user_name} ({user_id}) in guild={guild_id} channel={channel_id} params=[{params}]",
        "FR": "Commande slash /{command} appelee par {user_name} ({user_id}) dans serveur={guild_id} salon={channel_id} params=[{params}]",
    },
}


def tr(key: str, **kwargs: object) -> str:
    templates = _MESSAGES.get(key)
    if templates is None:
        return key
    template = templates.get(get_bot_lang()) or templates["EN"]
    return template.format(**kwargs)
