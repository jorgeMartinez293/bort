# services/scheduler/main.py
import time
import datetime
import logging
from services.shared.db import get_conn
from services.shared.queue import get_queue, enqueue_upload

logging.basicConfig(level=logging.INFO, format="%(asctime)s [scheduler] %(message)s")
log = logging.getLogger(__name__)

INTERVALS = {
    "hourly":   3600,
    "every_6h": 21600,
    "daily":    86400,
}

def _now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)

def _parse_ts(ts: str) -> datetime.datetime:
    dt = datetime.datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt

def tick():
    conn = get_conn()
    bots = conn.execute("SELECT * FROM bots WHERE active=1").fetchall()

    for bot in bots:
        schedule = bot["upload_schedule"]
        if schedule not in INTERVALS:
            continue  # 'manual' or unrecognised — skip

        interval_secs = INTERVALS[schedule]
        bot_id = bot["id"]

        # Don't dispatch if an upload is already in progress for this bot
        in_progress = conn.execute(
            "SELECT COUNT(*) FROM videos WHERE bot_id=? AND status='uploading'",
            (bot_id,)
        ).fetchone()[0]
        if in_progress:
            continue

        # Check time since last successful upload for this bot
        row = conn.execute(
            "SELECT MAX(u.published_at) as last_pub FROM uploads u "
            "JOIN videos v ON u.video_id = v.id "
            "WHERE v.bot_id=? AND u.status='done'",
            (bot_id,)
        ).fetchone()

        last_pub = row["last_pub"]
        if last_pub:
            elapsed = (_now_utc() - _parse_ts(last_pub)).total_seconds()
            if elapsed < interval_secs:
                continue

        # Get next queued video (FIFO)
        video = conn.execute(
            "SELECT id FROM videos WHERE bot_id=? AND status='approved' "
            "ORDER BY created_at ASC LIMIT 1",
            (bot_id,)
        ).fetchone()
        if not video:
            continue

        video_id = video["id"]
        conn.execute("UPDATE videos SET status='uploading' WHERE id=?", (video_id,))
        conn.execute(
            "INSERT INTO uploads (video_id, platform, status) VALUES (?, 'youtube', 'pending')",
            (video_id,)
        )
        conn.commit()
        enqueue_upload(get_queue("upload"), video_id=video_id)
        log.info("Dispatched video %d for bot %d (schedule: %s)", video_id, bot_id, schedule)

if __name__ == "__main__":
    log.info("Scheduler started")
    while True:
        try:
            tick()
        except Exception as e:
            log.error("Tick error: %s", e)
        time.sleep(60)
