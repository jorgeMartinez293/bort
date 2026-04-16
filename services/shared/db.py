# services/shared/db.py
import sqlite3, os
from typing import Optional

DB_PATH = os.environ.get("DB_PATH", "/data/db/bort.db")

_conn: Optional[sqlite3.Connection] = None

def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        if DB_PATH != ":memory:":
            parent = os.path.dirname(DB_PATH)
            if parent:
                os.makedirs(parent, exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA foreign_keys = ON")
    return _conn

def reset_conn():
    """For testing only — resets the singleton."""
    global _conn
    if _conn is not None:
        _conn.close()
    _conn = None

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            niche TEXT NOT NULL,
            subreddits TEXT NOT NULL,
            schedule_cron TEXT NOT NULL DEFAULT '0 */6 * * *',
            platforms TEXT NOT NULL DEFAULT '["youtube"]',
            background_mode TEXT NOT NULL DEFAULT 'random',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER NOT NULL REFERENCES bots(id),
            reddit_id TEXT NOT NULL UNIQUE,
            subreddit TEXT NOT NULL,
            raw_title TEXT NOT NULL,
            cleaned_script TEXT NOT NULL,
            upvotes INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL REFERENCES content(id),
            bot_id INTEGER NOT NULL REFERENCES bots(id),
            audio_path TEXT,
            video_path TEXT,
            duration_secs REAL,
            status TEXT NOT NULL DEFAULT 'pending_review',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER NOT NULL REFERENCES videos(id),
            platform TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            platform_video_id TEXT,
            published_at TIMESTAMP,
            error_msg TEXT
        );
    """)
    # Schema migrations — safe to run multiple times (ignored if column exists)
    for sql in [
        "ALTER TABLE bots ADD COLUMN yt_description TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE bots ADD COLUMN yt_tags TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE bots ADD COLUMN yt_privacy TEXT NOT NULL DEFAULT 'private'",
        "ALTER TABLE bots ADD COLUMN upload_schedule TEXT NOT NULL DEFAULT 'manual'",
        "ALTER TABLE content ADD COLUMN image_url TEXT",
    ]:
        try:
            conn.execute(sql)
        except Exception:
            pass
    conn.commit()
