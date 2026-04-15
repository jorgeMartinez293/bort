# services/api/ws.py
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from services.shared.queue import get_redis
from services.shared.db import get_conn

connected: list = []

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected.append(websocket)
    try:
        while True:
            redis = get_redis()
            conn = get_conn()
            payload = {
                "type": "status",
                "queues": {
                    "tts":    redis.llen("rq:queue:tts"),
                    "render": redis.llen("rq:queue:render"),
                },
                "pending_review": conn.execute(
                    "SELECT COUNT(*) FROM videos WHERE status='pending_review'"
                ).fetchone()[0],
            }
            await websocket.send_json(payload)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        connected.remove(websocket)
