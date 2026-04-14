# tests/shared/test_db.py
import pytest, os
os.environ["DB_PATH"] = ":memory:"

from services.shared.db import init_db, get_conn
from services.shared import db as db_module

@pytest.fixture(autouse=True)
def fresh_db():
    db_module.reset_conn()
    yield

def test_schema_creates_all_tables():
    conn = get_conn()
    init_db(conn)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = {row[0] for row in cursor.fetchall()}
    assert tables == {"bots", "content", "videos", "uploads"}

def test_bot_insert_and_fetch():
    conn = get_conn()
    init_db(conn)
    conn.execute(
        "INSERT INTO bots (name, niche, subreddits, schedule_cron, platforms, background_mode, active) "
        "VALUES (?,?,?,?,?,?,?)",
        ("did-you-know", "facts", '["todayilearned"]', "0 */6 * * *", '["youtube"]', "gameplay", 1)
    )
    conn.commit()
    row = conn.execute("SELECT name FROM bots WHERE name='did-you-know'").fetchone()
    assert row[0] == "did-you-know"
