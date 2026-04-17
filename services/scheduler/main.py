import time
import datetime
import logging
from typing import Optional
from services.shared.db import get_conn
from services.shared.queue import get_queue, enqueue_upload, enqueue_tts
from services.scraper.expander import gemini_elaborate_or_none

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


def retry_expand(conn, q) -> None:
    """Try to expand all expand_pending content. Stops on first Gemini failure."""
    rows = conn.execute(
        "SELECT id, cleaned_script FROM content WHERE status='expand_pending' ORDER BY id ASC"
    ).fetchall()
    for row in rows:
        elaboration = gemini_elaborate_or_none(row["cleaned_script"])
        if elaboration is None:
            break
        base = row["cleaned_script"].rstrip()
        if base and base[-1] not in ".!?":
            base += "."
        expanded = f"{base} {elaboration}"
        conn.execute(
            "UPDATE content SET cleaned_script=?, status='pending' WHERE id=?",
            (expanded, row["id"])
        )
        conn.commit()
        enqueue_tts(q, content_id=row["id"])
        log.info("Expanded and enqueued content %d", row["id"])


def tick(conn, q) -> None:
    bots = conn.execute("SELECT * FROM bots WHERE active=1").fetchall()

    for bot in bots:
        schedule = bot["upload_schedule"]
        if schedule not in INTERVALS:
            continue

        interval_secs = INTERVALS[schedule]
        bot_id = bot["id"]

        in_progress = conn.execute(
            "SELECT COUNT(*) FROM videos WHERE bot_id=? AND status='uploading'",
            (bot_id,)
        ).fetchone()[0]
        if in_progress:
            continue

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
        enqueue_upload(q, video_id=video_id)
        log.info("Dispatched video %d for bot %d (schedule: %s)", video_id, bot_id, schedule)


if __name__ == "__main__":
    log.info("Scheduler started")
    conn = get_conn()
    upload_q = get_queue("upload")
    tts_q = get_queue("tts")
    last_expand: Optional[datetime.datetime] = None

    while True:
        try:
            tick(conn, upload_q)
        except Exception as e:
            log.error("Tick error: %s", e)

        now = _now_utc()
        if last_expand is None or (now - last_expand).total_seconds() >= 3600:
            last_expand = now
            try:
                retry_expand(conn, tts_q)
            except Exception as e:
                log.error("retry_expand error: %s", e)

        time.sleep(60)
