# services/api/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from services.shared.db import get_conn, init_db
from services.api.routers import videos, bots, system, queue
from services.api.ws import websocket_endpoint

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(get_conn())
    yield

app = FastAPI(title="Bort API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos.router)
app.include_router(bots.router)
app.include_router(system.router)
app.include_router(queue.router)

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket_endpoint(websocket)
