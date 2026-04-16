# services/api/routers/videos.py
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from services.shared.db import get_conn
from services.scraper.cleaner import format_youtube_title

router = APIRouter(prefix="/api/videos", tags=["videos"])

class StatusUpdate(BaseModel):
    status: str

@router.get("")
def list_videos(status: str = "pending_review"):
    conn = get_conn()
    rows = conn.execute(
        "SELECT v.*, c.cleaned_script, c.raw_title, c.subreddit, c.upvotes "
        "FROM videos v JOIN content c ON v.content_id = c.id "
        "WHERE v.status=? ORDER BY v.created_at DESC",
        (status,)
    ).fetchall()
    result = []
    for r in rows:
        row = dict(r)
        row["youtube_title"] = format_youtube_title(row["raw_title"])
        result.append(row)
    return result

@router.patch("/{video_id}/status")
def update_status(video_id: int, body: StatusUpdate):
    allowed = {"approved", "rejected", "uploading", "uploaded", "upload_failed"}
    if body.status not in allowed:
        raise HTTPException(400, f"status must be one of {allowed}")
    conn = get_conn()
    cur = conn.execute("UPDATE videos SET status=? WHERE id=?", (body.status, video_id))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "Video not found")

    return {"ok": True, "video_id": video_id, "status": body.status}

@router.get("/{video_id}/stream")
def stream_video(video_id: int):
    conn = get_conn()
    row = conn.execute("SELECT video_path FROM videos WHERE id=?", (video_id,)).fetchone()
    if not row or not row["video_path"]:
        raise HTTPException(404, "Video not found")
    if not os.path.exists(row["video_path"]):
        raise HTTPException(404, "Video file not found on disk")
    return FileResponse(row["video_path"], media_type="video/mp4")

@router.get("/{video_id}/thumbnail")
def get_thumbnail(video_id: int):
    conn = get_conn()
    row = conn.execute("SELECT video_path FROM videos WHERE id=?", (video_id,)).fetchone()
    if not row or not row["video_path"]:
        raise HTTPException(404, "Video not found")
    thumb_path = os.path.splitext(row["video_path"])[0] + "_thumb.jpg"
    if not os.path.exists(thumb_path):
        raise HTTPException(404, "Thumbnail not available")
    return FileResponse(thumb_path, media_type="image/jpeg")
