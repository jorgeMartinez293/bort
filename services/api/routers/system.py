# services/api/routers/system.py
import os
import datetime
from fastapi import APIRouter
from services.shared.db import get_conn
from services.shared.queue import get_redis

_INTERVALS = {
    "hourly":   3600,
    "every_6h": 21600,
    "daily":    86400,
}

router = APIRouter(prefix="/api/system", tags=["system"])

@router.get("/status")
def system_status():
    redis = get_redis()
    conn = get_conn()
    return {
        "redis": redis.ping(),
        "queues": {
            "tts":    redis.llen("rq:queue:tts"),
            "render": redis.llen("rq:queue:render"),
            "upload": conn.execute(
                "SELECT COUNT(*) FROM videos WHERE status='approved'"
            ).fetchone()[0],
        },
        "counts": {
            "pending_review": conn.execute(
                "SELECT COUNT(*) FROM videos WHERE status='pending_review'"
            ).fetchone()[0],
            "published_today": conn.execute(
                "SELECT COUNT(*) FROM uploads WHERE status='done' "
                "AND date(published_at)=date('now')"
            ).fetchone()[0],
        }
    }

@router.get("/next-upload")
def next_upload():
    conn = get_conn()
    now = datetime.datetime.now(datetime.timezone.utc)
    bots = conn.execute("SELECT * FROM bots WHERE active=1").fetchall()
    result = []
    for bot in bots:
        schedule = bot["upload_schedule"]
        if schedule not in _INTERVALS:
            continue
        has_approved = conn.execute(
            "SELECT COUNT(*) FROM videos WHERE bot_id=? AND status='approved'",
            (bot["id"],)
        ).fetchone()[0]
        if not has_approved:
            continue
        in_progress = conn.execute(
            "SELECT COUNT(*) FROM videos WHERE bot_id=? AND status='uploading'",
            (bot["id"],)
        ).fetchone()[0]
        row = conn.execute(
            "SELECT MAX(u.published_at) as last_pub FROM uploads u "
            "JOIN videos v ON u.video_id = v.id "
            "WHERE v.bot_id=? AND u.status='done'",
            (bot["id"],)
        ).fetchone()
        last_pub = row["last_pub"]
        if last_pub:
            dt = datetime.datetime.fromisoformat(last_pub)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            seconds_until = max(0, _INTERVALS[schedule] - (now - dt).total_seconds())
        else:
            seconds_until = 0
        result.append({
            "bot_id":       bot["id"],
            "bot_name":     bot["name"],
            "schedule":     schedule,
            "seconds_until": int(seconds_until),
            "uploading":    bool(in_progress),
        })
    return result


@router.get("/gemini-status")
def gemini_status():
    conn = get_conn()
    return {
        "key_missing": not bool(os.environ.get("GEMINI_API_KEY")),
        "expand_pending_count": conn.execute(
            "SELECT COUNT(*) FROM content WHERE status='expand_pending'"
        ).fetchone()[0],
    }
