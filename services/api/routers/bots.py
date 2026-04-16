# services/api/routers/bots.py
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from services.shared.db import get_conn, init_db

router = APIRouter(prefix="/api/bots", tags=["bots"])

class BotCreate(BaseModel):
    name: str
    niche: str
    subreddits: List[str]
    schedule_cron: str = "0 */6 * * *"
    platforms: List[str] = ["youtube"]
    background_mode: str = "random"

UPLOAD_SCHEDULES = {"manual", "hourly", "every_6h", "daily"}

class BotUpdate(BaseModel):
    active: Optional[bool] = None
    schedule_cron: Optional[str] = None
    yt_description: Optional[str] = None
    yt_tags: Optional[List[str]] = None
    yt_privacy: Optional[str] = None
    upload_schedule: Optional[str] = None

@router.get("")
def list_bots():
    conn = get_conn()
    init_db(conn)
    rows = conn.execute("SELECT * FROM bots ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]

@router.post("", status_code=201)
def create_bot(body: BotCreate):
    conn = get_conn()
    init_db(conn)
    cur = conn.execute(
        "INSERT INTO bots (name, niche, subreddits, schedule_cron, platforms, background_mode, active) "
        "VALUES (?,?,?,?,?,?,1)",
        (body.name, body.niche, json.dumps(body.subreddits),
         body.schedule_cron, json.dumps(body.platforms), body.background_mode)
    )
    conn.commit()
    return {"id": cur.lastrowid}

@router.patch("/{bot_id}")
def update_bot(bot_id: int, body: BotUpdate):
    if all(v is None for v in [body.active, body.schedule_cron, body.yt_description, body.yt_tags, body.yt_privacy, body.upload_schedule]):
        raise HTTPException(422, "At least one field must be provided")
    conn = get_conn()
    if body.active is not None:
        conn.execute("UPDATE bots SET active=? WHERE id=?", (int(body.active), bot_id))
    if body.schedule_cron is not None:
        conn.execute("UPDATE bots SET schedule_cron=? WHERE id=?", (body.schedule_cron, bot_id))
    if body.yt_description is not None:
        conn.execute("UPDATE bots SET yt_description=? WHERE id=?", (body.yt_description, bot_id))
    if body.yt_tags is not None:
        conn.execute("UPDATE bots SET yt_tags=? WHERE id=?", (json.dumps(body.yt_tags), bot_id))
    if body.yt_privacy is not None:
        if body.yt_privacy not in ("private", "public"):
            raise HTTPException(422, "yt_privacy must be 'private' or 'public'")
        conn.execute("UPDATE bots SET yt_privacy=? WHERE id=?", (body.yt_privacy, bot_id))
    if body.upload_schedule is not None:
        if body.upload_schedule not in UPLOAD_SCHEDULES:
            raise HTTPException(422, f"upload_schedule must be one of {UPLOAD_SCHEDULES}")
        conn.execute("UPDATE bots SET upload_schedule=? WHERE id=?", (body.upload_schedule, bot_id))
    conn.commit()
    return {"ok": True}
