# BGA Discord self-host bot

[Version francaise](README.fr.md)

Self-hosted Discord bot for Board Game Arena.

The bot watches public BGA tables in spectator mode, without cookies or BGA login, then posts a status message in Discord for each watched table.

Target workflow:
- you manually link a Discord member with `/bga link-member @discord BgaName BgaId`
- the link can be partial: name only, ID only, or both
- the bot fills the missing field automatically when it observes a table
- you add a BGA table with `/bga watch <full_url>`
- the bot detects whose turn it is
- it creates, updates, deletes, then recreates Discord messages as turns evolve
- when the game is over, it removes the last active message and automatically removes the watch

## Quick start

After cloning the repository and installing `requirements.txt`, you can start the bot directly with `python -m bga_turn`.

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

## 1. Deployment

### Requirements

- Python 3.11 or newer recommended
- a Discord bot created in the Discord developer portal
- the bot invited to your Discord server
- one or more BGA tables publicly accessible in spectator mode

### Project structure

- `bot.py`: development launcher from the repository root
- `src/bga_turn/app.py`: application entry point
- `src/bga_turn/commands_bga.py`: `/bga` slash commands
- `src/bga_turn/bga_client.py`: public BGA networking, HTML parsing, websocket handling
- `src/bga_turn/monitor.py`: watch loop and Discord publishing logic
- `src/bga_turn/database.py`: SQLite persistence
- `src/bga_turn/models.py`: domain dataclasses
- `src/bga_turn/utils.py`: URL parsing, JSON helpers, small utilities
- `src/bga_turn/schema.sql`: packaged SQLite schema
- `pyproject.toml`: package metadata and console entry point
- `requirements.txt`: installs the project itself in editable mode
- `LICENSE`: MIT license
- `.github/workflows/ci.yml`: lightweight validation on push and pull request
- `.env.example`: local configuration example

### Local installation

From the project directory:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Adjust the virtual environment activation and file copy commands to your shell if needed.

Then edit `.env`:

```env
DISCORD_TOKEN=paste_your_bot_token_here
DISCORD_GUILD_ID=paste_your_server_id_here
DISCORD_CLEAR_GLOBAL_COMMANDS=0
BGA_POLL_SECONDS=15
BGA_DB_PATH=bga_bot.db
BGA_WS_URL=wss://ws-x1.boardgamearena.com/connection/websocket
BGA_ENABLE_TABLEINFOS_FALLBACK=0
LOG_LEVEL=INFO
BOT_LANG=EN
```

### `.env` variables

- `DISCORD_TOKEN`: required; copy it from the Discord Developer Portal, in your application, under `Bot`
- `DISCORD_GUILD_ID`: optional but strongly recommended for the first setup; copy your server ID from the Discord client after enabling Developer Mode
- `DISCORD_CLEAR_GLOBAL_COMMANDS`: optional, set to `1` once to delete stale global slash commands before guild sync, then set it back to `0`
- `BGA_POLL_SECONDS`: supervision interval for the monitor scheduler
- `BGA_DB_PATH`: SQLite file path
- `BGA_WS_URL`: public BGA websocket endpoint
- `BGA_ENABLE_TABLEINFOS_FALLBACK`: optional, `0` by default; when set to `1`, re-enables the HTTP `tableinfos.html` fallback used when the websocket is silent
- `LOG_LEVEL`: console log level
- `BOT_LANG`: bot language for internal logs, slash command responses, and Discord messages, `EN` by default, `FR` for French

### Discord setup for beginners

#### 1. Create the Discord application and bot

1. Go to `https://discord.com/developers/applications`
2. Click `New Application`
3. Give the application a name, then create it
4. Open the application and go to the `Bot` tab
5. If Discord asks, click `Add Bot`
6. In the `Bot` tab:
   - click `Reset Token` or `Copy` to get the bot token
   - paste that value into `DISCORD_TOKEN=...` in your `.env`
   - keep this token secret; if it is ever exposed, regenerate it immediately
7. You do not need to enable privileged intents for this project

#### 2. Invite the bot to your Discord server

1. In the Discord Developer Portal, open the `Installation` page
2. For `Guild Install`, make sure the install link includes:
   - `bot`
   - `applications.commands`
3. For the bot permissions, the tested minimum is:
   - `View Channels`
   - `Send Messages`
   - `Embed Links`
   - `Read Message History`
4. Copy the generated install link
5. Open that link in your browser
6. Choose the Discord server where you want the bot
7. Approve the installation

If your Developer Portal UI still shows `OAuth2 > URL Generator` instead of `Installation`, do the same there:
- select `bot`
- select `applications.commands`
- select the permissions above
- open the generated URL and add the bot to your server

#### 3. Get `DISCORD_GUILD_ID`

`DISCORD_GUILD_ID` is optional, but it is the easiest way to make slash commands appear almost immediately while you are setting the bot up.

To get it:

1. Open the Discord app
2. Go to `User Settings > Advanced`
3. Enable `Developer Mode`
4. Right-click your server icon or server name
5. Click `Copy Server ID`
6. Paste that value into `DISCORD_GUILD_ID=...` in your `.env`

If you leave `DISCORD_GUILD_ID` empty, the bot still works, but slash command updates can take longer to appear because they are synced globally.

#### 4. Example `.env` for a first setup

```env
DISCORD_TOKEN=paste_your_bot_token_here
DISCORD_GUILD_ID=paste_your_server_id_here
DISCORD_CLEAR_GLOBAL_COMMANDS=0
BGA_POLL_SECONDS=15
BGA_DB_PATH=bga_bot.db
BGA_WS_URL=wss://ws-x1.boardgamearena.com/connection/websocket
BGA_ENABLE_TABLEINFOS_FALLBACK=0
LOG_LEVEL=INFO
BOT_LANG=EN
```

Quick explanation:
- `DISCORD_TOKEN`: the secret token copied from the `Bot` tab in the Discord Developer Portal
- `DISCORD_GUILD_ID`: your Discord server ID, copied from the Discord client with Developer Mode enabled
- `BOT_LANG`: set `EN` for English or `FR` for French

If slash commands appear twice because you previously used global commands, set `DISCORD_CLEAR_GLOBAL_COMMANDS=1` for one startup, let the bot delete the old global commands, then set it back to `0`.

### Run the bot

#### Recommended

```bash
python -m bga_turn
```

or

```bash
bga-turn-bot
```

#### Optional development launcher

```bash
python bot.py
```

If `DISCORD_GUILD_ID` is set, slash commands are synced to that guild. Otherwise, they are synced globally, which may take longer.

If you previously used global slash commands and now see duplicates together with guild-scoped commands, set `DISCORD_CLEAR_GLOBAL_COMMANDS=1` for one startup, let the bot delete the stale global commands, then set it back to `0`.

### License

This repository is distributed under the MIT license. See `LICENSE`.

### SQLite database

The project uses SQLite with 3 useful tables.

#### `users`

Maps a Discord member to a BGA player.

A link can be partial:
- `bga_player_id` can be empty
- `bga_player_name` can be empty
- logically, at least one of them must be provided

Main columns:
- `discord_user_id`
- `bga_player_id`
- `bga_player_name`

#### `watch_subscriptions`

Describes watched tables per guild/channel.

Main columns:
- `subscription_id`
- `table_id`
- `table_url`
- `guild_id`
- `channel_id`
- `created_by_discord_user_id`

#### `watch_states`

Stores the last known state for a watch.

Main columns:
- `subscription_id`
- `last_packet_id`
- `last_waiting_ids`
- `last_player_names`
- `is_initialized`
- `game_name`

## 2. Discord commands

All commands are under the `/bga` group.

### `/bga link-member`

Manually link a Discord member to a BGA player.

Syntax:

```text
/bga link-member @Member Haurrus 91713763
```

or

```text
/bga link-member @Member Haurrus
```

or

```text
/bga link-member @Member "" 91713763
```

Usage:
- requires `Manage Server` or `Administrator`
- stores the `Discord -> BGA` mapping
- accepts a partial link: name only, ID only, or both
- the bot fills the missing field automatically when it recognizes the player on a watched table
- used later for Discord mentions in turn messages

### `/bga unlink-member`

Remove the BGA link for a Discord member.

Syntax:

```text
/bga unlink-member @Member
```

### `/bga linked`

Show all Discord members currently linked to a BGA ID.

Syntax:

```text
/bga linked
```

### `/bga watch`

Add a public BGA table to watch in the current channel.

Syntax:

```text
/bga watch https://en.boardgamearena.com/15/sevenwondersdice?table=827248309
```

Rules:
- the command requires the full public BGA table URL
- the watch is attached to the current guild and channel
- the websocket worker starts immediately after the command, without waiting for the next scheduler cycle

### `/bga unwatch`

Remove a watch for the table in the current channel.

Syntax:

```text
/bga unwatch 827248309
```

or

```text
/bga unwatch https://en.boardgamearena.com/15/sevenwondersdice?table=827248309
```

### `/bga unwatch-all`

Remove all watches from the current server.

Syntax:

```text
/bga unwatch-all
```

Usage:
- requires `Manage Server` or `Administrator`
- useful to reset everything cleanly

### `/bga watchlist`

Show all watched tables on the current server.

Syntax:

```text
/bga watchlist
```

### `/bga status`

Show the last known state of watched tables on the current server.

Syntax:

```text
/bga status
```

Displays, among other things:
- table
- channel
- known `waiting_ids`
- interpreted state

### Full setup example

1. Link a Discord player to a BGA ID:

```text
/bga link-member @MrHaurrus Haurrus 91713763
```

2. Add a table to watch:

```text
/bga watch https://en.boardgamearena.com/6/perfectwords?table=827318521
```

3. Check watched tables:

```text
/bga watchlist
```

4. Check the current state:

```text
/bga status
```

## 3. Technical overview

### High-level view

The bot has 3 layers:
- Discord: slash commands and message publishing
- SQLite: persistence for links and watches
- Public BGA: table page bootstrap + public websocket connection

### BGA network flow

The bot does not use cookies, browser sessions, or BGA login.

The network flow is the following.

#### 1. Load the public table page

The bot downloads the public table URL, for example:

```text
https://en.boardgamearena.com/6/perfectwords?table=827318521
```

From that HTML it extracts:
- anonymous spectator identity
  - `user_id`
  - `current_player_name`
  - `archivemask`, reused as websocket `credentials`
- known player names from the HTML bootstrap
- the initial game state when available
  - especially `gamestate.active_player` for single-active-player games

#### 2. Open the public websocket

The bot then opens the public BGA websocket:

```text
wss://ws-x1.boardgamearena.com/connection/websocket
```

It replays the BGA/Centrifugo handshake:
- `connect`
- `subscribe bgamsg`
- `subscribe /general/emergency`
- `subscribe /player/p<visitor_id>`
- `subscribe /table/t<TABLE_ID>`
- `presence /table/t<TABLE_ID>`

#### 3. Interpret events

The bot reconstructs `waiting_ids` with this priority order:

1. `gameStateMultipleActiveUpdate`
2. `gameStateChange.active_player` for single-active-player games
3. `yourturnack` as a light fallback
4. limited public heuristics on some events (`beginTurn`, `endPrivateAction`, etc.)

To detect that a game is finished, the bot also uses:

1. `tableInfosChanged` with `status = finished`
2. `tableInfosChanged.reload_reason = tableDestroy`
3. end-of-game events visible in the public stream (`End of game`, `simpleNote`, `simpleNode`)

By default, the bot does not use `tableinfos.html` as an end-of-game fallback anymore, because this public endpoint is inconsistent without an authenticated BGA session. If you want to restore that legacy behavior, set `BGA_ENABLE_TABLEINFOS_FALLBACK=1`.

#### 4. Single-active vs multi-active games

The behavior is designed not to break multi-active games.

- If the public page exposes a `gamestate` of type `activeplayer`, the bot can initialize `waiting_ids` immediately from `active_player`.
- If the public page exposes a `multipleactiveplayer` state, the bot does not invent anything from HTML bootstrap and waits for websocket events, especially `gameStateMultipleActiveUpdate`.

In practice:
- `Perfectwords` benefits from HTML bootstrap immediately
- `Seven Wonders Dice` is still driven mainly by `gameStateMultipleActiveUpdate`

### Discord message behavior

For each watched table:
- the bot creates a message when an active turn starts
- it edits that message while the waiting list shrinks
- it deletes that message when the turn is over
- it creates a new message for the next turn
- if the BGA game is detected as finished, it deletes the last active message and automatically removes the watch

On bot startup:
- it removes old bot messages linked to each watched table in the channel
- then republishes a clean current state

This cleanup is targeted:
- only bot messages containing `Table : <table_id>` are removed
- the rest of the channel is untouched

### Python architecture

#### `src/bga_turn/app.py`

Responsibilities:
- load `.env`
- initialize logging
- open the SQLite database
- instantiate `BgaClient`
- instantiate `BgaMonitor`
- start the Discord bot
- sync slash commands

#### `bot.py`

Responsibilities:
- act as an optional development launcher from the repository root
- add `src/` to `sys.path`
- forward execution to the packaged application in `src/bga_turn`

#### `src/bga_turn/commands_bga.py`

Responsibilities:
- expose `/bga` commands
- validate Discord permissions
- parse table URLs
- store watches and Discord/BGA links
- support partial links and automatic enrichment
- trigger an immediate monitor refresh after `/bga watch`, `/bga unwatch`, and `/bga unwatch-all`

#### `src/bga_turn/database.py`

Responsibilities:
- create and migrate the SQLite database
- read and write user mappings
- read and write watches
- store the last known state per watch

#### `src/bga_turn/bga_client.py`

Responsibilities:
- download the public table page
- extract useful HTML bootstrap data
- open and maintain the public BGA websocket connection
- parse websocket messages
- detect end-of-game transitions from the websocket
- optionally use `tableinfos.html` as a legacy fallback when explicitly enabled
- produce `BgaNotificationState` objects

#### `src/bga_turn/monitor.py`

Responsibilities:
- start one websocket worker per watched table
- compare old and new states
- decide when to create, update, or delete Discord messages
- clean old messages on startup
- automatically delete the active message and remove the watch when a game is over

#### `src/bga_turn/utils.py`

Responsibilities:
- parse BGA URLs
- JSON helpers
- small formatting and utility helpers

### Important notes and limits

- the bot only works for BGA tables publicly accessible in spectator mode
- the bot is self-hosted: it must keep running on your machine to keep watching tables
- Discord voice warnings (`PyNaCl`, `davey`) are not relevant for this project
- the `message content intent` warning is not blocking here because the bot relies on slash commands
- displayed game names come from the BGA slug or public bootstrap, so they are not always perfectly formatted
- the project currently ships without a unit test suite; validation is kept lightweight through packaging and compilation checks
