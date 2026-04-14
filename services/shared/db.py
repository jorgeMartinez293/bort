# services/shared/db.py
import sqlite3, os

DB_PATH = os.environ.get("DB_PATH", "/data/db/bort.db")

def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) if DB_PATH != ":memory:" else None
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

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
    conn.commit()
