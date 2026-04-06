# Bot Discord BGA self-host

[English version](README.md)

Bot Discord self-host pour Board Game Arena.

Le bot surveille des tables BGA publiques en mode spectateur, sans cookies ni login BGA, puis publie dans Discord un message de statut par table surveillee.

Le workflow cible est simple :
- tu lies manuellement un membre Discord avec `/bga link-member @discord NomBGA IDBGA`
- le lien peut etre partiel : seul le nom, seul l'ID, ou les deux
- le bot enrichit automatiquement le champ manquant quand il observe une table
- tu ajoutes une table BGA avec `/bga watch <url_complete>`
- le bot detecte qui doit jouer
- il cree, met a jour, supprime puis recree les messages Discord au rythme des tours
- quand la partie est terminee, il supprime le dernier message actif et retire automatiquement la watch

## Demarrage rapide

Apres avoir clone le depot et installe `requirements.txt`, tu peux lancer directement le bot avec `python -m bga_turn`.

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m bga_turn
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m bga_turn
```

## 1. Deploiement

### Prerequis

- Python 3.11 ou plus recent recommande
- un bot Discord cree dans le portail developpeur Discord
- le bot invite sur ton serveur Discord
- une ou plusieurs tables BGA accessibles publiquement en mode spectateur

### Structure du projet

- `bot.py` : lanceur de dev depuis la racine du depot
- `src/bga_turn/app.py` : point d'entree principal de l'application
- `src/bga_turn/commands_bga.py` : slash commands `/bga`
- `src/bga_turn/bga_client.py` : acces reseau BGA public, parsing HTML + websocket
- `src/bga_turn/monitor.py` : logique de surveillance et publication Discord
- `src/bga_turn/database.py` : persistance SQLite
- `src/bga_turn/models.py` : dataclasses metier
- `src/bga_turn/utils.py` : parsing URL, JSON, helpers divers
- `src/bga_turn/schema.sql` : schema SQLite embarque dans le package
- `pyproject.toml` : metadata du package et point d'entree console
- `requirements.txt` : installe le projet lui-meme en mode editable
- `LICENSE` : licence MIT
- `.github/workflows/ci.yml` : validation legere sur les pushes et pull requests
- `.env.example` : exemple de configuration locale

### Installation locale

Depuis le dossier du projet :

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Adapte simplement les commandes d'activation de l'environnement virtuel et de copie de fichier a ton shell.

Edite ensuite `.env` :

```env
DISCORD_TOKEN=ton_token_bot
DISCORD_GUILD_ID=
DISCORD_CLEAR_GLOBAL_COMMANDS=0
BGA_POLL_SECONDS=15
BGA_DB_PATH=bga_bot.db
BGA_WS_URL=wss://ws-x1.boardgamearena.com/connection/websocket
BGA_ENABLE_TABLEINFOS_FALLBACK=0
LOG_LEVEL=INFO
BOT_LANG=EN
```

### Signification des variables `.env`

- `DISCORD_TOKEN` : token du bot Discord
- `DISCORD_GUILD_ID` : optionnel, permet une synchro quasi immediate des slash commands sur un serveur precis
- `DISCORD_CLEAR_GLOBAL_COMMANDS` : optionnel, mets `1` une seule fois pour supprimer d'anciennes slash commands globales avant la sync guilde, puis remets `0`
- `BGA_POLL_SECONDS` : rythme de supervision du scheduler du monitor
- `BGA_DB_PATH` : chemin du fichier SQLite
- `BGA_WS_URL` : endpoint websocket public BGA
- `BGA_ENABLE_TABLEINFOS_FALLBACK` : optionnel, `0` par defaut ; si tu mets `1`, tu reactive le fallback HTTP `tableinfos.html` utilise quand le websocket devient silencieux
- `LOG_LEVEL` : niveau de logs console
- `BOT_LANG` : langue du bot, appliquee aux logs internes, aux reponses des slash commands et aux messages Discord, `EN` par defaut, `FR` pour le francais

### Creer et inviter le bot Discord

1. Va sur `https://discord.com/developers/applications`
2. Cree une application
3. Va dans l'onglet `Bot`
4. Recupere le token du bot et place-le dans `.env`
5. Va dans `OAuth2 > URL Generator`
6. Coche `bot` et `applications.commands`
7. Invite le bot sur ton serveur

### Lancement

#### Recommande

```bash
python -m bga_turn
```

ou

```bash
bga-turn-bot
```

#### Lanceur de dev optionnel

```bash
python bot.py
```

Si `DISCORD_GUILD_ID` est renseigne, les slash commands seront synchronisees sur cette guilde. Sinon, elles seront synchronisees globalement, ce qui peut prendre plus de temps.

Si tu utilisais auparavant des slash commands globales et que tu vois maintenant des doublons avec les commandes de guilde, mets `DISCORD_CLEAR_GLOBAL_COMMANDS=1` le temps d'un demarrage, laisse le bot supprimer les anciennes commandes globales, puis remets `0`.

### Licence

Ce depot est distribue sous licence MIT. Voir `LICENSE`.

### Base SQLite

Le projet utilise SQLite avec 3 tables utiles.

#### `users`

Associe un membre Discord a un joueur BGA.

Un lien peut etre partiel :
- `bga_player_id` peut etre vide
- `bga_player_name` peut etre vide
- au moins un des deux doit etre renseigne logiquement

Colonnes principales :
- `discord_user_id`
- `bga_player_id`
- `bga_player_name`

#### `watch_subscriptions`

Decrit les tables surveillees par serveur/salon.

Colonnes principales :
- `subscription_id`
- `table_id`
- `table_url`
- `guild_id`
- `channel_id`
- `created_by_discord_user_id`

#### `watch_states`

Conserve le dernier etat connu d'une surveillance.

Colonnes principales :
- `subscription_id`
- `last_packet_id`
- `last_waiting_ids`
- `last_player_names`
- `is_initialized`
- `game_name`

## 2. Commandes Discord

Toutes les commandes sont dans le groupe `/bga`.

### `/bga link-member`

Lie manuellement un membre Discord a un joueur BGA.

Syntaxe :

```text
/bga link-member @Membre Haurrus 91713763
```

ou

```text
/bga link-member @Membre Haurrus
```

ou

```text
/bga link-member @Membre "" 91713763
```

Usage :
- necessite `Manage Server` ou `Administrator`
- enregistre le mapping `Discord -> BGA`
- accepte un lien partiel : nom seul, ID seul, ou les deux
- le bot complete automatiquement le champ manquant quand il reconnait le joueur dans une table
- sert ensuite pour les mentions dans les messages de tour

### `/bga unlink-member`

Supprime le lien BGA d'un membre Discord.

Syntaxe :

```text
/bga unlink-member @Membre
```

### `/bga linked`

Affiche tous les membres Discord actuellement lies a un ID BGA.

Syntaxe :

```text
/bga linked
```

### `/bga watch`

Ajoute une table BGA publique a surveiller dans le salon courant.

Syntaxe :

```text
/bga watch https://en.boardgamearena.com/15/sevenwondersdice?table=827248309
```

Regles :
- la commande exige l'URL publique complete de la table BGA
- la watch est associee au serveur et au salon courant
- le worker websocket est demarre immediatement apres la commande, sans attendre le prochain cycle du scheduler

### `/bga unwatch`

Supprime une watch pour la table dans le salon courant.

Syntaxe :

```text
/bga unwatch 827248309
```

ou

```text
/bga unwatch https://en.boardgamearena.com/15/sevenwondersdice?table=827248309
```

### `/bga unwatch-all`

Supprime toutes les watches du serveur courant.

Syntaxe :

```text
/bga unwatch-all
```

Usage :
- necessite `Manage Server` ou `Administrator`
- utile pour repartir proprement

### `/bga watchlist`

Affiche toutes les tables surveillees sur le serveur courant.

Syntaxe :

```text
/bga watchlist
```

### `/bga status`

Affiche l'etat connu des watches sur le serveur courant.

Syntaxe :

```text
/bga status
```

Affiche notamment :
- table
- salon
- `waiting_ids` connus
- etat interprete

### Exemple de mise en service complete

1. Lier un joueur Discord a son ID BGA :

```text
/bga link-member @MrHaurrus Haurrus 91713763
```

2. Ajouter une table a surveiller :

```text
/bga watch https://en.boardgamearena.com/6/perfectwords?table=827318521
```

3. Verifier les watches :

```text
/bga watchlist
```

4. Verifier l'etat courant :

```text
/bga status
```

## 3. Fonctionnement technique

### Vue d'ensemble

Le bot repose sur 3 couches :
- Discord : reception des slash commands et publication des messages
- SQLite : persistance des liens Discord/BGA et des watches
- BGA public : lecture de la page publique de table + connexion au websocket public

### Fonctionnement reseau cote BGA

Le bot n'utilise pas de cookies, pas de session navigateur, pas de login BGA.

Le flux reseau est le suivant.

#### 1. Lecture de la page publique

Le bot telecharge l'URL publique de la table, par exemple :

```text
https://en.boardgamearena.com/6/perfectwords?table=827318521
```

Dans ce HTML, il extrait :
- l'identite spectateur anonyme
  - `user_id`
  - `current_player_name`
  - `archivemask`, reutilise comme `credentials` websocket
- les noms des joueurs connus dans le bootstrap HTML
- l'etat initial du jeu si disponible
  - en particulier `gamestate.active_player` pour les jeux mono-actifs

#### 2. Connexion websocket publique

Le bot ouvre ensuite le websocket public BGA :

```text
wss://ws-x1.boardgamearena.com/connection/websocket
```

Puis il rejoue le handshake BGA/Centrifugo :
- `connect`
- `subscribe bgamsg`
- `subscribe /general/emergency`
- `subscribe /player/p<visitor_id>`
- `subscribe /table/t<TABLE_ID>`
- `presence /table/t<TABLE_ID>`

#### 3. Interpretation des evenements

Le bot reconstruit l'etat des joueurs attendus (`waiting_ids`) avec cet ordre de priorite :

1. `gameStateMultipleActiveUpdate`
2. `gameStateChange.active_player` pour les jeux mono-actifs
3. `yourturnack` comme fallback leger
4. heuristiques publiques limitees sur certains evenements (`beginTurn`, `endPrivateAction`, etc.)

Pour detecter la fin d'une partie, le bot utilise en plus :

1. `tableInfosChanged` avec `status = finished`
2. `tableInfosChanged.reload_reason = tableDestroy`
3. les evenements de fin visibles dans le flux (`End of game`, `simpleNote`, `simpleNode`)

Par defaut, le bot n'utilise plus `tableinfos.html` comme fallback de fin de partie, car cet endpoint public est trop incoherent sans session BGA authentifiee. Si tu veux retrouver ce comportement historique, mets `BGA_ENABLE_TABLEINFOS_FALLBACK=1`.

#### 4. Difference mono-actif / multi-actif

Le comportement a ete pense pour ne pas casser les jeux multi-actifs.

- Si la page publique expose un `gamestate` de type `activeplayer`, le bot peut initialiser tout de suite `waiting_ids` depuis `active_player`.
- Si la page publique expose un etat `multipleactiveplayer`, le bot n'invente rien au bootstrap HTML et attend le websocket, en particulier `gameStateMultipleActiveUpdate`.

Concretement :
- `Perfectwords` beneficie du bootstrap HTML initial
- `Seven Wonders Dice` reste pilote surtout par `gameStateMultipleActiveUpdate`

### Fonctionnement des messages Discord

Pour chaque table surveillee :
- le bot cree un message quand un tour actif commence
- il edite ce message tant que la liste des joueurs attendus se reduit
- il supprime ce message quand le tour est fini
- il cree un nouveau message au tour suivant
- si la partie BGA est detectee comme terminee, il supprime le dernier message actif et retire automatiquement la watch

Au demarrage du bot :
- il nettoie les anciens messages du bot lies a chaque table surveillee dans le salon
- il republie ensuite un etat propre

Le nettoyage est cible :
- seuls les messages du bot contenant `Table : <table_id>` sont supprimes
- le reste du salon n'est pas touche

### Architecture Python

#### `src/bga_turn/app.py`

Responsabilites :
- charge `.env`
- initialise les logs
- ouvre la base SQLite
- instancie `BgaClient`
- instancie `BgaMonitor`
- demarre le bot Discord
- synchronise les slash commands

#### `bot.py`

Responsabilites :
- sert de lanceur de dev optionnel depuis la racine du depot
- ajoute `src/` au `sys.path`
- redirige l'execution vers l'application packagee dans `src/bga_turn`

#### `src/bga_turn/commands_bga.py`

Responsabilites :
- expose les commandes `/bga`
- valide les permissions Discord
- parse les URLs de table
- enregistre les watches et les liens Discord/BGA
- autorise les liens partiels et leur enrichissement automatique
- declenche un rafraichissement immediat du monitor apres `/bga watch`, `/bga unwatch` et `/bga unwatch-all`

#### `src/bga_turn/database.py`

Responsabilites :
- cree et migre la base SQLite
- lit et ecrit les mappings utilisateurs
- lit et ecrit les watches
- conserve le dernier etat connu par watch

#### `src/bga_turn/bga_client.py`

Responsabilites :
- telecharge la page publique de table
- extrait le bootstrap HTML utile
- ouvre et maintient la connexion websocket publique BGA
- parse les messages websocket
- detecte les fins de partie via websocket
- peut utiliser `tableinfos.html` comme fallback legacy uniquement si tu l'actives explicitement
- produit des objets `BgaNotificationState`

#### `src/bga_turn/monitor.py`

Responsabilites :
- lance un worker websocket par table surveillee
- compare l'ancien et le nouvel etat
- decide quand creer, modifier ou supprimer les messages Discord
- nettoie les anciens messages au demarrage
- supprime automatiquement le message actif et la watch quand la partie est terminee

#### `src/bga_turn/utils.py`

Responsabilites :
- parse les URLs BGA
- helpers JSON
- normalisation de petits formats utilitaires

### Points importants et limites

- le bot ne fonctionne que sur des tables BGA accessibles publiquement en mode spectateur
- le bot est self-host : il doit tourner sur ta machine pour surveiller les tables
- les warnings Discord lies a la voix (`PyNaCl`, `davey`) ne sont pas bloquants pour ce projet
- le warning `message content intent` n'est pas bloquant ici car le bot repose sur des slash commands
- les noms de jeux affiches viennent du slug BGA ou du bootstrap public, donc ils ne sont pas toujours joliment formates
- le projet est actuellement distribue sans suite de tests unitaires ; la validation reste volontairement legere via le packaging et la compilation
