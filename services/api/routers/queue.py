# services/api/routers/queue.py
from fastapi import APIRouter, HTTPException
from services.shared.db import get_conn
from services.shared.queue import get_queue, enqueue_upload
from services.scraper.cleaner import format_youtube_title

router = APIRouter(prefix="/api/queue", tags=["queue"])

@router.get("")
def list_queue():
    conn = get_conn()
    rows = conn.execute(
        "SELECT v.*, c.cleaned_script, c.raw_title, c.subreddit, c.upvotes, b.name as bot_name "
        "FROM videos v "
        "JOIN content c ON v.content_id = c.id "
        "JOIN bots b ON v.bot_id = b.id "
        "WHERE v.status='approved' ORDER BY v.created_at ASC"
    ).fetchall()
    result = []
    for i, r in enumerate(rows):
        row = dict(r)
        row["youtube_title"] = format_youtube_title(row["raw_title"])
        row["queue_position"] = i + 1
        result.append(row)
    return result

@router.post("/{video_id}/dequeue")
def dequeue_video(video_id: int):
    conn = get_conn()
    row = conn.execute("SELECT status FROM videos WHERE id=?", (video_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Video not found")
    if row["status"] != "approved":
        raise HTTPException(409, f"Video is not in queue (status: {row['status']})")
    conn.execute("UPDATE videos SET status='pending_review' WHERE id=?", (video_id,))
    conn.commit()
    return {"ok": True, "video_id": video_id}

@router.post("/{video_id}/trigger")
def trigger_upload(video_id: int):
    conn = get_conn()
    row = conn.execute("SELECT status FROM videos WHERE id=?", (video_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Video not found")
    if row["status"] != "approved":
        raise HTTPException(409, f"Video is not in queue (status: {row['status']})")

    conn.execute("UPDATE videos SET status='uploading' WHERE id=?", (video_id,))
    conn.execute(
        "INSERT INTO uploads (video_id, platform, status) VALUES (?, 'youtube', 'pending')",
        (video_id,),
    )
    conn.commit()
    enqueue_upload(get_queue("upload"), video_id=video_id)
    return {"ok": True, "video_id": video_id}
