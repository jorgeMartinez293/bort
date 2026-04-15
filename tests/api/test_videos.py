import os, pytest
os.environ["DB_PATH"] = ":memory:"
os.environ["MEDIA_PATH"] = "/tmp/bort_test_media"

from fastapi.testclient import TestClient
from services.api.main import app
from services.shared.db import get_conn, init_db, reset_conn

@pytest.fixture(autouse=True)
def setup_db():
    reset_conn()
    conn = get_conn()
    init_db(conn)
    # Seed a bot and a video
    conn.execute(
        "INSERT INTO bots (name, niche, subreddits, platforms, background_mode, active) "
        "VALUES ('test-bot','facts','[]','[]','random',1)"
    )
    conn.execute(
        "INSERT INTO content (bot_id, reddit_id, subreddit, raw_title, cleaned_script, upvotes, status) "
        "VALUES (1,'abc','todayilearned','TIL test','Did you know test',9999,'rendered')"
    )
    conn.execute(
        "INSERT INTO videos (content_id, bot_id, audio_path, video_path, duration_secs, status) "
        "VALUES (1,1,'/tmp/audio.wav','/tmp/video.mp4',42.0,'pending_review')"
    )
    conn.commit()

client = TestClient(app)

def test_list_pending_videos_returns_200():
    response = client.get("/api/videos?status=pending_review")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "pending_review"

def test_approve_video_changes_status():
    response = client.patch("/api/videos/1/status", json={"status": "approved"})
    assert response.status_code == 200
    check = client.get("/api/videos?status=approved")
    assert len(check.json()) == 1

def test_reject_video_changes_status():
    response = client.patch("/api/videos/1/status", json={"status": "rejected"})
    assert response.status_code == 200
