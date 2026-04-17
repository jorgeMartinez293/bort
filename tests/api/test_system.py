import os
os.environ["DB_PATH"] = ":memory:"
os.environ["MEDIA_PATH"] = "/tmp/bort_test_media"

import pytest
from fastapi.testclient import TestClient
from services.api.main import app
from services.shared.db import get_conn, init_db, reset_conn

@pytest.fixture(autouse=True)
def setup_db():
    reset_conn()
    conn = get_conn()
    init_db(conn)
    conn.execute(
        "INSERT INTO bots (name, niche, subreddits, platforms, background_mode, active) "
        "VALUES ('test-bot','facts','[]','[]','random',1)"
    )
    conn.commit()

client = TestClient(app)


def test_gemini_status_key_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    conn = get_conn()
    conn.execute(
        "INSERT INTO content (bot_id, reddit_id, subreddit, raw_title, cleaned_script, upvotes, status) "
        "VALUES (1,'abc','todayilearned','TIL test','short',999,'expand_pending')"
    )
    conn.commit()
    resp = client.get("/api/system/gemini-status")
    assert resp.status_code == 200
    assert resp.json()["key_missing"] is True
    assert resp.json()["expand_pending_count"] == 1


def test_gemini_status_key_present(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    resp = client.get("/api/system/gemini-status")
    assert resp.status_code == 200
    assert resp.json()["key_missing"] is False
    assert resp.json()["expand_pending_count"] == 0
