# services/shared/queue.py
import os
import rq
from redis import Redis
from typing import Optional

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

_redis: Optional[Redis] = None

def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(REDIS_URL)
    return _redis

def get_queue(name: str) -> rq.Queue:
    return rq.Queue(name, connection=get_redis())

def enqueue_tts(q: rq.Queue, content_id: int) -> rq.job.Job:
    return q.enqueue(
        "services.tts.main.process_content",
        kwargs={"content_id": content_id},
        job_id=f"tts-{content_id}",
        job_timeout=300,
    )

def enqueue_render(q: rq.Queue, content_id: int) -> rq.job.Job:
    return q.enqueue(
        "services.video.main.process_content",
        kwargs={"content_id": content_id},
        job_id=f"render-{content_id}",
        job_timeout=600,
    )

def enqueue_upload(q: rq.Queue, video_id: int) -> rq.job.Job:
    return q.enqueue(
        "services.upload.main.process_upload",
        kwargs={"video_id": video_id},
        job_id=f"upload-{video_id}",
        job_timeout=600,
    )
