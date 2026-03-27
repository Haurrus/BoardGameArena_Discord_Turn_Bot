# Bot Discord BGA self-host

[English version](README.en.md)

Bot Discord self-host pour Board Game Arena.

Le bot surveille des tables BGA publiques en mode spectateur, sans cookies ni login BGA, puis publie dans Discord un message de statut par table surveillee.

Le workflow cible est simple :
- tu lies manuellement un membre Discord a son `bga_player_id`
- tu ajoutes une table BGA avec `/bga watch <url_complete>`
- le bot detecte qui doit jouer
- il cree, met a jour, supprime puis recree les messages Discord au rythme des tours
- quand la partie est terminee, il supprime le dernier message actif et retire automatiquement la watch

## 1. Deploiement

### Prerequis

- Python 3.11 ou plus recent recommande
- un bot Discord cree dans le portail developpeur Discord
- le bot invite sur ton serveur Discord
- une ou plusieurs tables BGA accessibles publiquement en mode spectateur

### Structure du projet

- `bot.py` : point d'entree du bot Discord
- `commands_bga.py` : slash commands `/bga`
- `bga_client.py` : acces reseau BGA public, parsing HTML + websocket
- `monitor.py` : logique de surveillance et publication Discord
- `database.py` : persistance SQLite
- `models.py` : dataclasses metier
- `utils.py` : parsing URL, JSON, helpers divers
- `schema.sql` : schema SQLite
- `requirements.txt` : dependances Python
- `.env.example` : exemple de configuration locale

### Installation locale

Depuis le dossier du projet :

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Adapte simplement les commandes d'activation de l'environnement virtuel et de copie de fichier a ton shell.

Edite ensuite `.env` :

```env
DISCORD_TOKEN=ton_token_bot
DISCORD_GUILD_ID=
BGA_POLL_SECONDS=15
BGA_DB_PATH=bga_bot.db
BGA_WS_URL=wss://ws-x1.boardgamearena.com/connection/websocket
LOG_LEVEL=INFO
```

### Signification des variables `.env`

- `DISCORD_TOKEN` : token du bot Discord
- `DISCORD_GUILD_ID` : optionnel, permet une synchro quasi immediate des slash commands sur un serveur precis
- `BGA_POLL_SECONDS` : rythme de supervision du scheduler du monitor
- `BGA_DB_PATH` : chemin du fichier SQLite
- `BGA_WS_URL` : endpoint websocket public BGA
- `LOG_LEVEL` : niveau de logs console

### Creer et inviter le bot Discord

1. Va sur `https://discord.com/developers/applications`
2. Cree une application
3. Va dans l'onglet `Bot`
4. Recupere le token du bot et place-le dans `.env`
5. Va dans `OAuth2 > URL Generator`
6. Coche `bot` et `applications.commands`
7. Invite le bot sur ton serveur

### Lancement

```bash
python bot.py
```

Si `DISCORD_GUILD_ID` est renseigne, les slash commands seront synchronisees sur cette guilde. Sinon, elles seront synchronisees globalement, ce qui peut prendre plus de temps.

### Base SQLite

Le projet utilise SQLite avec 3 tables utiles.

#### `users`

Associe un membre Discord a un joueur BGA.

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
/bga link-member @Membre 91713763 Haurrus
```

Usage :
- necessite `Manage Server` ou `Administrator`
- enregistre le mapping `Discord -> BGA`
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
- la commande attend une URL complete publique de table
- le bot extrait `table_id`, `gameserver` et `game_name` depuis l'URL
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
/bga link-member @MrHaurrus 91713763 Haurrus
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
4. un controle de secours sur `tableinfos.html` quand le websocket devient silencieux

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

#### `bot.py`

Responsabilites :
- charge `.env`
- initialise les logs
- ouvre la base SQLite
- instancie `BgaClient`
- instancie `BgaMonitor`
- demarre le bot Discord
- synchronise les slash commands

#### `commands_bga.py`

Responsabilites :
- expose les commandes `/bga`
- valide les permissions Discord
- parse les URLs de table
- enregistre les watches et les liens Discord/BGA
- declenche un rafraichissement immediat du monitor apres `/bga watch`, `/bga unwatch` et `/bga unwatch-all`

#### `database.py`

Responsabilites :
- cree et migre la base SQLite
- lit et ecrit les mappings utilisateurs
- lit et ecrit les watches
- conserve le dernier etat connu par watch

#### `bga_client.py`

Responsabilites :
- telecharge la page publique de table
- extrait le bootstrap HTML utile
- ouvre et maintient la connexion websocket publique BGA
- parse les messages websocket
- detecte les fins de partie via websocket ou via `tableinfos.html`
- produit des objets `BgaNotificationState`

#### `monitor.py`

Responsabilites :
- lance un worker websocket par table surveillee
- compare l'ancien et le nouvel etat
- decide quand creer, modifier ou supprimer les messages Discord
- nettoie les anciens messages au demarrage
- supprime automatiquement le message actif et la watch quand la partie est terminee

#### `utils.py`

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

## Commande de lancement rapide

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

Adapte seulement l'activation du venv et la commande de copie si ton shell utilise une syntaxe differente.
