# BGA Discord self-host bot

[Version francaise](README.md)

Self-hosted Discord bot for Board Game Arena.

The bot watches public BGA tables in spectator mode, without cookies or BGA login, then posts a status message in Discord for each watched table.

Target workflow:
- you manually link a Discord member to a `bga_player_id`
- you add a BGA table with `/bga watch <full_url>`
- the bot detects whose turn it is
- it creates, updates, deletes, then recreates Discord messages as turns evolve

## 1. Deployment

### Requirements

- Python 3.11 or newer recommended
- a Discord bot created in the Discord developer portal
- the bot invited to your Discord server
- one or more BGA tables publicly accessible in spectator mode

### Project structure

- `bot.py`: Discord bot entry point
- `commands_bga.py`: `/bga` slash commands
- `bga_client.py`: public BGA networking, HTML parsing, websocket handling
- `monitor.py`: watch loop and Discord publishing logic
- `database.py`: SQLite persistence
- `models.py`: domain dataclasses
- `utils.py`: URL parsing, JSON helpers, small utilities
- `schema.sql`: SQLite schema
- `requirements.txt`: Python dependencies
- `.env.example`: local configuration example

### Local installation

From the project directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Adjust the virtual environment activation and file copy commands to your shell if needed.

Then edit `.env`:

```env
DISCORD_TOKEN=your_bot_token
DISCORD_GUILD_ID=
BGA_POLL_SECONDS=15
BGA_DB_PATH=bga_bot.db
BGA_WS_URL=wss://ws-x1.boardgamearena.com/connection/websocket
LOG_LEVEL=INFO
```

### `.env` variables

- `DISCORD_TOKEN`: Discord bot token
- `DISCORD_GUILD_ID`: optional, enables near-instant slash command sync for one guild
- `BGA_POLL_SECONDS`: supervision interval for table workers on the bot side
- `BGA_DB_PATH`: SQLite file path
- `BGA_WS_URL`: public BGA websocket endpoint
- `LOG_LEVEL`: console log level

### Create and invite the Discord bot

1. Go to `https://discord.com/developers/applications`
2. Create an application
3. Open the `Bot` tab
4. copy the bot token into `.env`
5. Open `OAuth2 > URL Generator`
6. Check `bot` and `applications.commands`
7. Invite the bot to your server

### Run the bot

```bash
python bot.py
```

If `DISCORD_GUILD_ID` is set, slash commands are synced to that guild. Otherwise, they are synced globally, which may take longer.

### SQLite database

The project uses SQLite with 3 useful tables.

#### `users`

Maps a Discord member to a BGA player.

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
/bga link-member @Member 91713763 Haurrus
```

Usage:
- requires `Manage Server` or `Administrator`
- stores the `Discord -> BGA` mapping
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
- the command expects a full public table URL
- the bot extracts `table_id`, `gameserver`, and `game_name` from the URL
- the watch is attached to the current guild and channel

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
/bga link-member @MrHaurrus 91713763 Haurrus
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

On bot startup:
- it removes old bot messages linked to each watched table in the channel
- then republishes a clean current state

This cleanup is targeted:
- only bot messages containing `Table : <table_id>` are removed
- the rest of the channel is untouched

### Python architecture

#### `bot.py`

Responsibilities:
- load `.env`
- initialize logging
- open the SQLite database
- instantiate `BgaClient`
- instantiate `BgaMonitor`
- start the Discord bot
- sync slash commands

#### `commands_bga.py`

Responsibilities:
- expose `/bga` commands
- validate Discord permissions
- parse table URLs
- store watches and Discord/BGA links

#### `database.py`

Responsibilities:
- create and migrate the SQLite database
- read and write user mappings
- read and write watches
- store the last known state per watch

#### `bga_client.py`

Responsibilities:
- download the public table page
- extract useful HTML bootstrap data
- open and maintain the public BGA websocket connection
- parse websocket messages
- produce `BgaNotificationState` objects

#### `monitor.py`

Responsibilities:
- start one websocket worker per watched table
- compare old and new states
- decide when to create, update, or delete Discord messages
- clean old messages on startup

#### `utils.py`

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

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

Adjust only the venv activation and file copy commands if your shell uses a different syntax.
