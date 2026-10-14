-- WA00 proposal for WA01/WA02. Synthetic fixture schema, not a migration runner.
PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;
CREATE TABLE chats (
    jid TEXT PRIMARY KEY NOT NULL CHECK(length(jid) > 0),
    name TEXT,
    last_message_time TEXT
);
CREATE TABLE messages (
    id TEXT NOT NULL CHECK(length(id) > 0),
    chat_jid TEXT NOT NULL,
    sender TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    timestamp TEXT NOT NULL,
    is_from_me INTEGER NOT NULL CHECK(is_from_me IN (0, 1)),
    media_type TEXT NOT NULL DEFAULT '',
    -- Legacy columns retained for compatibility; new collector leaves these NULL.
    filename TEXT, url TEXT, media_key BLOB,
    file_sha256 BLOB, file_enc_sha256 BLOB, file_length INTEGER,
    PRIMARY KEY (id, chat_jid),
    FOREIGN KEY (chat_jid) REFERENCES chats(jid)
);
CREATE INDEX messages_order ON messages(timestamp, chat_jid, id);
CREATE INDEX messages_chat_order ON messages(chat_jid, timestamp, id);
CREATE TABLE collector_status (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    linked INTEGER NOT NULL CHECK(linked IN (0, 1)),
    connected INTEGER NOT NULL CHECK(connected IN (0, 1)),
    heartbeat_at TEXT NOT NULL,
    last_connected_at TEXT,
    last_receive_at TEXT,
    last_db_update_at TEXT,
    last_sync_attempt_at TEXT,
    last_history_event_at TEXT,
    error_class TEXT,
    partial_history INTEGER NOT NULL DEFAULT 1 CHECK(partial_history = 1),
    synthetic INTEGER NOT NULL DEFAULT 0 CHECK(synthetic IN (0, 1))
);
