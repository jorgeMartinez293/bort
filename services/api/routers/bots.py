# services/api/routers/bots.py
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from services.shared.db import get_conn

router = APIRouter(prefix="/api/bots", tags=["bots"])

class BotCreate(BaseModel):
    name: str
    niche: str
    subreddits: List[str]
    schedule_cron: str = "0 */6 * * *"
    platforms: List[str] = ["youtube"]
    background_mode: str = "random"

class BotUpdate(BaseModel):
    active: Optional[bool] = None
    schedule_cron: Optional[str] = None

@router.get("")
def list_bots():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM bots ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]

@router.post("", status_code=201)
def create_bot(body: BotCreate):
    conn = get_conn()
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
    if body.active is None and body.schedule_cron is None:
        raise HTTPException(422, "At least one field must be provided")
    conn = get_conn()
    if body.active is not None:
        conn.execute("UPDATE bots SET active=? WHERE id=?", (int(body.active), bot_id))
    if body.schedule_cron is not None:
        conn.execute("UPDATE bots SET schedule_cron=? WHERE id=?", (body.schedule_cron, bot_id))
    conn.commit()
    return {"ok": True}
