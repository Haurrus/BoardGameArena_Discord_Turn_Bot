PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    discord_user_id TEXT PRIMARY KEY,
    bga_player_id TEXT NOT NULL,
    bga_player_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watch_subscriptions (
    subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id TEXT NOT NULL,
    table_url TEXT,
    base_url TEXT,
    gameserver TEXT,
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    created_by_discord_user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(table_id, guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS watch_states (
    subscription_id INTEGER PRIMARY KEY,
    last_packet_id INTEGER NOT NULL DEFAULT 1,
    last_waiting_ids TEXT NOT NULL DEFAULT '[]',
    last_player_names TEXT NOT NULL DEFAULT '{}',
    is_initialized INTEGER NOT NULL DEFAULT 0,
    game_name TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (subscription_id) REFERENCES watch_subscriptions(subscription_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_watch_subscriptions_table_id ON watch_subscriptions(table_id);
