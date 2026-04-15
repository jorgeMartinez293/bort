# services/api/routers/system.py
from fastapi import APIRouter
from services.shared.db import get_conn
from services.shared.queue import get_redis

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
            "upload": redis.llen("rq:queue:upload"),
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
