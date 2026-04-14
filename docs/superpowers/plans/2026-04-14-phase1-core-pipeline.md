# Bort Phase 1 — Core Pipeline + Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete pipeline from Reddit scraping to video review — runnable with `docker compose up` on MacBook, deployable to RPi5.

**Architecture:** Seven Docker services (redis, scraper, tts-worker, video-worker, api, ui, nginx) orchestrated by Docker Compose. Redis + rq decouple pipeline stages. SQLite on NVMe stores state. Generated media lives on HDD. The dashboard is a React PWA served by Nginx, FastAPI behind `/api`. HTTPS via `tailscale cert` in production.

**Tech Stack:** Python 3.12, PRAW, Piper TTS, faster-whisper, FFmpeg, Redis + rq, SQLite (aiosqlite), FastAPI, React 18 + Vite + vite-plugin-pwa, Nginx, Docker Compose

---

## File Map

```
bort/
├── docker-compose.yml            # dev — bind mounts, libx264, ports exposed
├── docker-compose.prod.yml       # prod override — h264_v4l2m2m, Tailscale HTTPS
├── .env.example
├── .gitignore
│
├── services/
│   ├── shared/
│   │   ├── db.py                 # SQLite schema creation + connection helper
│   │   ├── models.py             # Dataclasses for Bot, Content, Video, Upload
│   │   └── queue.py              # Redis connection + rq queue helpers
│   │
│   ├── scraper/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── reddit.py             # PRAW wrapper: fetch + filter posts
│   │   ├── cleaner.py            # Strip TIL format, add hook + CTA
│   │   └── main.py               # Scheduler (runs scrape every 6h)
│   │
│   ├── tts/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── piper_tts.py          # Piper TTS wrapper → WAV file
│   │   ├── whisper_timestamps.py # faster-whisper → word-level timestamps
│   │   └── main.py               # rq worker: content_id → audio + timestamps
│   │
│   ├── video/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── subtitles.py          # word timestamps → ASS subtitle file
│   │   ├── renderer.py           # FFmpeg command builder + executor
│   │   └── main.py               # rq worker: content_id → MP4
│   │
│   └── api/
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── main.py               # FastAPI app, mounts routers
│       ├── routers/
│       │   ├── videos.py         # GET /videos, PATCH /videos/{id}/status, GET /videos/{id}/stream
│       │   ├── bots.py           # GET/POST/PATCH /bots
│       │   └── system.py         # GET /system/status
│       └── ws.py                 # WebSocket /ws — broadcasts status events
│
├── dashboard/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── public/
│   │   └── manifest.json         # PWA manifest
│   └── src/
│       ├── main.tsx
│       ├── App.tsx               # Router setup
│       ├── api/
│       │   └── client.ts         # fetch wrapper + WebSocket hook
│       ├── components/
│       │   ├── Topbar.tsx
│       │   ├── Sidebar.tsx
│       │   └── VideoCard.tsx
│       └── pages/
│           ├── Pending.tsx
│           ├── Published.tsx
│           ├── Rejected.tsx
│           └── Settings.tsx
│
└── nginx/
    ├── Dockerfile
    └── nginx.conf                # serves /  → dashboard, proxies /api + /ws → api
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `services/shared/__init__.py` (empty)

- [ ] **Step 1: Create root `.gitignore`**

```gitignore
.env
__pycache__/
*.pyc
.pytest_cache/
node_modules/
dist/
.superpowers/
/data/
/media/
*.db
```

- [ ] **Step 2: Create `.env.example`**

```env
# Reddit OAuth2 — register app at https://www.reddit.com/prefs/apps
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=bort/0.1 by u/yourusername

# Paths (override for prod to point at NVMe/HDD mount points)
DB_PATH=/data/db/bort.db
MEDIA_PATH=/media
REDIS_URL=redis://redis:6379/0

# Video encoder: libx264 (dev/Mac) or h264_v4l2m2m (RPi5)
VIDEO_ENCODER=libx264
```

- [ ] **Step 3: Create `docker-compose.yml` (dev)**

All Python services share the same `./services` mount at `/app/services` with `PYTHONPATH=/app`. This makes imports identical in Docker and in tests (`from services.shared.db import ...`).

```yaml
services:
  redis:
    image: redis:7-alpine
    volumes:
      - ./data/redis:/data
    ports:
      - "6379:6379"

  scraper:
    build: ./services/scraper
    env_file: .env
    environment:
      PYTHONPATH: /app
    volumes:
      - ./services:/app/services
      - ./data:/data
      - ./media:/media
    depends_on: [redis]
    command: python -m services.scraper.main

  tts-worker:
    build: ./services/tts
    env_file: .env
    environment:
      PYTHONPATH: /app
    volumes:
      - ./services:/app/services
      - ./data:/data
      - ./media:/media
    depends_on: [redis]
    command: python -m services.tts.main

  video-worker:
    build: ./services/video
    env_file: .env
    environment:
      PYTHONPATH: /app
    volumes:
      - ./services:/app/services
      - ./data:/data
      - ./media:/media
    depends_on: [redis]
    command: python -m services.video.main

  api:
    build: ./services/api
    env_file: .env
    environment:
      PYTHONPATH: /app
    volumes:
      - ./services:/app/services
      - ./data:/data
      - ./media:/media
    depends_on: [redis]
    ports:
      - "8000:8000"
    command: uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload --app-dir /app

  ui:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - ./dashboard:/app
    ports:
      - "5173:5173"
    command: sh -c "npm install && npm run dev -- --host"

  nginx:
    build: ./nginx
    ports:
      - "80:80"
    depends_on: [api, ui]
```

- [ ] **Step 4: Create data/media directories and package `__init__.py` files**

```bash
mkdir -p data/db data/redis media/backgrounds/gameplay media/backgrounds/images \
         media/generated/audio media/generated/videos media/archive

# Make all service directories Python packages
touch services/__init__.py
touch services/shared/__init__.py
touch services/scraper/__init__.py
touch services/tts/__init__.py
touch services/video/__init__.py
touch services/api/__init__.py
touch services/api/routers/__init__.py
```

- [ ] **Step 5: Commit**

```bash
git init
git add docker-compose.yml .env.example .gitignore
git commit -m "chore: project scaffold and docker-compose"
```

---

## Task 2: Shared Database Schema

**Files:**
- Create: `services/shared/db.py`
- Create: `services/shared/models.py`
- Create: `tests/shared/test_db.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/shared/test_db.py
import pytest, os, tempfile
os.environ["DB_PATH"] = ":memory:"

from services.shared.db import init_db, get_conn

def test_schema_creates_all_tables():
    conn = get_conn()
    init_db(conn)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert tables == {"bots", "content", "videos", "uploads"}

def test_bot_insert_and_fetch():
    conn = get_conn()
    init_db(conn)
    conn.execute(
        "INSERT INTO bots (name, niche, subreddits, schedule_cron, platforms, background_mode, active) "
        "VALUES (?,?,?,?,?,?,?)",
        ("did-you-know", "facts", '["todayilearned"]', "0 */6 * * *", '["youtube"]', "gameplay", 1)
    )
    conn.commit()
    row = conn.execute("SELECT name FROM bots WHERE name='did-you-know'").fetchone()
    assert row[0] == "did-you-know"
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /path/to/bort
python -m pytest tests/shared/test_db.py -v
```

Expected: `ModuleNotFoundError: No module named 'services'`

- [ ] **Step 3: Implement `services/shared/models.py`**

```python
# services/shared/models.py
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Bot:
    id: Optional[int]
    name: str
    niche: str
    subreddits: list[str]      # stored as JSON
    schedule_cron: str
    platforms: list[str]       # stored as JSON
    background_mode: str       # "gameplay" | "images" | "random"
    active: bool
    created_at: Optional[datetime] = None

@dataclass
class Content:
    id: Optional[int]
    bot_id: int
    reddit_id: str
    subreddit: str
    raw_title: str
    cleaned_script: str
    upvotes: int
    status: str   # pending | tts_queued | tts_done | render_queued | rendered | skip
    created_at: Optional[datetime] = None

@dataclass
class Video:
    id: Optional[int]
    content_id: int
    bot_id: int
    audio_path: Optional[str]
    video_path: Optional[str]
    duration_secs: Optional[float]
    status: str   # pending_review | approved | rejected | uploading | uploaded
    created_at: Optional[datetime] = None

@dataclass
class Upload:
    id: Optional[int]
    video_id: int
    platform: str
    status: str   # pending | uploading | done | failed
    platform_video_id: Optional[str]
    published_at: Optional[datetime]
    error_msg: Optional[str]
```

- [ ] **Step 4: Implement `services/shared/db.py`**

```python
# services/shared/db.py
import sqlite3, os

DB_PATH = os.environ.get("DB_PATH", "/data/db/bort.db")

def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) if DB_PATH != ":memory:" else None
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            niche TEXT NOT NULL,
            subreddits TEXT NOT NULL,
            schedule_cron TEXT NOT NULL DEFAULT '0 */6 * * *',
            platforms TEXT NOT NULL DEFAULT '["youtube"]',
            background_mode TEXT NOT NULL DEFAULT 'random',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER NOT NULL REFERENCES bots(id),
            reddit_id TEXT NOT NULL UNIQUE,
            subreddit TEXT NOT NULL,
            raw_title TEXT NOT NULL,
            cleaned_script TEXT NOT NULL,
            upvotes INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL REFERENCES content(id),
            bot_id INTEGER NOT NULL REFERENCES bots(id),
            audio_path TEXT,
            video_path TEXT,
            duration_secs REAL,
            status TEXT NOT NULL DEFAULT 'pending_review',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER NOT NULL REFERENCES videos(id),
            platform TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            platform_video_id TEXT,
            published_at TIMESTAMP,
            error_msg TEXT
        );
    """)
    conn.commit()
```

- [ ] **Step 5: Add `tests/shared/__init__.py` and `tests/__init__.py` (empty), then run tests**

```bash
touch tests/__init__.py tests/shared/__init__.py
PYTHONPATH=. python -m pytest tests/shared/test_db.py -v
```

Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add services/shared/ tests/shared/
git commit -m "feat: shared db schema and models"
```

---

## Task 3: Shared Redis Queue Helpers

**Files:**
- Create: `services/shared/queue.py`
- Create: `tests/shared/test_queue.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/shared/test_queue.py
import pytest
from unittest.mock import patch, MagicMock

def test_enqueue_tts_job_puts_content_id_on_queue():
    with patch("services.shared.queue.rq.Queue") as MockQueue:
        mock_q = MagicMock()
        MockQueue.return_value = mock_q
        from services.shared.queue import enqueue_tts, get_queue
        q = get_queue("tts")
        enqueue_tts(q, content_id=42)
        mock_q.enqueue.assert_called_once()
        call_args = mock_q.enqueue.call_args
        assert call_args[1]["kwargs"]["content_id"] == 42

def test_enqueue_render_job_puts_content_id_on_queue():
    with patch("services.shared.queue.rq.Queue") as MockQueue:
        mock_q = MagicMock()
        MockQueue.return_value = mock_q
        from services.shared.queue import enqueue_render, get_queue
        q = get_queue("render")
        enqueue_render(q, content_id=42)
        mock_q.enqueue.assert_called_once()
```

- [ ] **Step 2: Run to confirm failure**

```bash
PYTHONPATH=. python -m pytest tests/shared/test_queue.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `services/shared/queue.py`**

```python
# services/shared/queue.py
import os
import rq
from redis import Redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

def get_redis() -> Redis:
    return Redis.from_url(REDIS_URL)

def get_queue(name: str) -> rq.Queue:
    return rq.Queue(name, connection=get_redis())

def enqueue_tts(q: rq.Queue, content_id: int) -> rq.job.Job:
    return q.enqueue("services.tts.main.process_content", kwargs={"content_id": content_id}, job_timeout=300)

def enqueue_render(q: rq.Queue, content_id: int) -> rq.job.Job:
    return q.enqueue("services.video.main.process_content", kwargs={"content_id": content_id}, job_timeout=600)
```

- [ ] **Step 4: Install rq in a venv and run tests**

```bash
python -m venv .venv && source .venv/bin/activate
pip install rq redis pytest
PYTHONPATH=. python -m pytest tests/shared/ -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add services/shared/queue.py tests/shared/test_queue.py
git commit -m "feat: shared redis queue helpers"
```

---

## Task 4: Script Cleaner

**Files:**
- Create: `services/scraper/cleaner.py`
- Create: `tests/scraper/test_cleaner.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/scraper/test_cleaner.py
from services.scraper.cleaner import clean_til, is_suitable

def test_strips_til_prefix():
    result = clean_til("TIL that honey never expires.")
    assert not result.startswith("TIL")
    assert "honey never expires" in result

def test_strips_til_without_that():
    result = clean_til("TIL honey bees can recognize human faces.")
    assert not result.startswith("TIL")

def test_adds_hook_prefix():
    result = clean_til("TIL that octopuses have three hearts.")
    assert result.startswith("Did you know")

def test_strips_markdown_links():
    result = clean_til("TIL that [Wikipedia](https://en.wikipedia.org) exists.")
    assert "https://" not in result
    assert "[Wikipedia]" not in result

def test_is_suitable_passes_high_upvote_novel_post():
    assert is_suitable(upvotes=5000, reddit_id="abc123", seen_ids=set()) is True

def test_is_suitable_rejects_low_upvotes():
    assert is_suitable(upvotes=100, reddit_id="abc123", seen_ids=set()) is False

def test_is_suitable_rejects_duplicate():
    assert is_suitable(upvotes=10000, reddit_id="abc123", seen_ids={"abc123"}) is False

def test_script_max_length():
    long_text = "word " * 200
    result = clean_til("TIL that " + long_text)
    assert len(result.split()) <= 160
```

- [ ] **Step 2: Run to confirm all fail**

```bash
PYTHONPATH=. python -m pytest tests/scraper/test_cleaner.py -v
```

- [ ] **Step 3: Implement `services/scraper/cleaner.py`**

```python
# services/scraper/cleaner.py
import re

MIN_UPVOTES = 3_000
MAX_WORDS = 150

def clean_til(raw_title: str) -> str:
    """Strip TIL prefix, clean markdown, add hook, truncate to MAX_WORDS."""
    # Remove TIL prefix variants
    text = re.sub(r"^TIL\s+(that\s+)?", "", raw_title, flags=re.IGNORECASE).strip()
    # Strip markdown links: [text](url) → text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Strip bare URLs
    text = re.sub(r"https?://\S+", "", text)
    # Strip leftover markdown
    text = re.sub(r"[*_`]", "", text)
    text = text.strip()
    # Capitalize first letter
    if text:
        text = text[0].upper() + text[1:]
    # Truncate
    words = text.split()
    if len(words) > MAX_WORDS:
        text = " ".join(words[:MAX_WORDS]) + "."
    # Add hook
    return f"Did you know that {text[0].lower()}{text[1:]}"

def is_suitable(upvotes: int, reddit_id: str, seen_ids: set) -> bool:
    """Return True if the post should be turned into a video."""
    if upvotes < MIN_UPVOTES:
        return False
    if reddit_id in seen_ids:
        return False
    return True
```

- [ ] **Step 4: Run tests**

```bash
touch tests/scraper/__init__.py
PYTHONPATH=. python -m pytest tests/scraper/test_cleaner.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add services/scraper/cleaner.py tests/scraper/
git commit -m "feat: reddit script cleaner with TIL stripping and hook injection"
```

---

## Task 5: Reddit Client (Scraper)

**Files:**
- Create: `services/scraper/reddit.py`
- Create: `tests/scraper/test_reddit.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/scraper/test_reddit.py
from unittest.mock import MagicMock, patch
from services.scraper.reddit import fetch_posts

def _make_post(id_, title, score):
    p = MagicMock()
    p.id = id_
    p.title = title
    p.score = score
    p.subreddit.display_name = "todayilearned"
    return p

def test_fetch_posts_returns_cleaned_list():
    mock_sub = MagicMock()
    mock_sub.hot.return_value = [
        _make_post("aaa", "TIL that honey never expires.", 50_000),
        _make_post("bbb", "TIL octopuses have three hearts", 25_000),
    ]
    with patch("services.scraper.reddit.praw.Reddit") as MockReddit:
        MockReddit.return_value.subreddit.return_value = mock_sub
        posts = fetch_posts(
            subreddit="todayilearned",
            limit=10,
            seen_ids=set(),
            client_id="x", client_secret="y", user_agent="test"
        )
    assert len(posts) == 2
    assert posts[0]["reddit_id"] == "aaa"
    assert posts[0]["cleaned_script"].startswith("Did you know")
    assert posts[0]["upvotes"] == 50_000

def test_fetch_posts_skips_seen_ids():
    mock_sub = MagicMock()
    mock_sub.hot.return_value = [
        _make_post("aaa", "TIL that honey never expires.", 50_000),
    ]
    with patch("services.scraper.reddit.praw.Reddit") as MockReddit:
        MockReddit.return_value.subreddit.return_value = mock_sub
        posts = fetch_posts(
            subreddit="todayilearned", limit=10,
            seen_ids={"aaa"},
            client_id="x", client_secret="y", user_agent="test"
        )
    assert posts == []
```

- [ ] **Step 2: Run to confirm failure**

```bash
PYTHONPATH=. python -m pytest tests/scraper/test_reddit.py -v
```

- [ ] **Step 3: Implement `services/scraper/reddit.py`**

```python
# services/scraper/reddit.py
import praw
from services.scraper.cleaner import clean_til, is_suitable

def fetch_posts(
    subreddit: str,
    limit: int,
    seen_ids: set,
    client_id: str,
    client_secret: str,
    user_agent: str,
) -> list[dict]:
    """Fetch top posts from a subreddit, filter and clean them."""
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )
    results = []
    for post in reddit.subreddit(subreddit).hot(limit=limit):
        if not is_suitable(post.score, post.id, seen_ids):
            continue
        results.append({
            "reddit_id": post.id,
            "subreddit": post.subreddit.display_name,
            "raw_title": post.title,
            "cleaned_script": clean_til(post.title),
            "upvotes": post.score,
        })
    return results
```

- [ ] **Step 4: Install praw and run tests**

```bash
pip install praw
PYTHONPATH=. python -m pytest tests/scraper/ -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add services/scraper/reddit.py tests/scraper/test_reddit.py
git commit -m "feat: reddit client with PRAW, filtering and cleaning"
```

---

## Task 6: Scraper Main (Scheduler)

**Files:**
- Create: `services/scraper/main.py`
- Create: `services/scraper/requirements.txt`
- Create: `services/scraper/Dockerfile`

- [ ] **Step 1: Implement `services/scraper/main.py`**

```python
# services/scraper/main.py
import os, json, logging, schedule, time

from services.shared.db import get_conn, init_db
from services.shared.queue import get_queue, enqueue_tts
from services.scraper.reddit import fetch_posts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [scraper] %(message)s")
log = logging.getLogger(__name__)

BOT_ID = 1  # Phase 1: single bot, seeded in DB on first run

def seed_default_bot(conn):
    existing = conn.execute("SELECT id FROM bots WHERE id=1").fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO bots (id, name, niche, subreddits, schedule_cron, platforms, background_mode, active) "
            "VALUES (1,'did-you-know','facts','[\"todayilearned\",\"interestingasfuck\"]','0 */6 * * *','[\"youtube\"]','random',1)"
        )
        conn.commit()
        log.info("Seeded default bot")

def run_scrape():
    conn = get_conn()
    init_db(conn)
    seed_default_bot(conn)

    bot = conn.execute("SELECT * FROM bots WHERE id=?", (BOT_ID,)).fetchone()
    subreddits = json.loads(bot["subreddits"])
    seen = {r["reddit_id"] for r in conn.execute("SELECT reddit_id FROM content").fetchall()}

    q = get_queue("tts")
    total = 0
    for sub in subreddits:
        posts = fetch_posts(
            subreddit=sub,
            limit=25,
            seen_ids=seen,
            client_id=os.environ["REDDIT_CLIENT_ID"],
            client_secret=os.environ["REDDIT_CLIENT_SECRET"],
            user_agent=os.environ["REDDIT_USER_AGENT"],
        )
        for post in posts:
            cur = conn.execute(
                "INSERT INTO content (bot_id, reddit_id, subreddit, raw_title, cleaned_script, upvotes, status) "
                "VALUES (?,?,?,?,?,?,'pending')",
                (BOT_ID, post["reddit_id"], post["subreddit"], post["raw_title"], post["cleaned_script"], post["upvotes"])
            )
            conn.commit()
            enqueue_tts(q, content_id=cur.lastrowid)
            seen.add(post["reddit_id"])
            total += 1
    log.info(f"Scraped {total} new posts")

if __name__ == "__main__":
    log.info("Scraper starting — running immediately then every 6h")
    run_scrape()
    schedule.every(6).hours.do(run_scrape)
    while True:
        schedule.run_pending()
        time.sleep(60)
```

- [ ] **Step 2: Create `services/scraper/requirements.txt`**

```
praw==7.7.1
schedule==1.2.1
rq==1.16.1
redis==5.0.1
```

- [ ] **Step 3: Create `services/scraper/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# services/ is bind-mounted in dev; CMD uses full module path
CMD ["python", "-m", "services.scraper.main"]
```

- [ ] **Step 4: Commit**

```bash
git add services/scraper/
git commit -m "feat: scraper scheduler — fetches Reddit every 6h and enqueues TTS jobs"
```

---

## Task 7: Piper TTS Wrapper

**Files:**
- Create: `services/tts/piper_tts.py`
- Create: `tests/tts/test_piper_tts.py`

**Pre-requisite:** Download a Piper TTS voice model. Run once:
```bash
mkdir -p media/tts_models
cd media/tts_models
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```
Set `PIPER_MODEL_PATH=/media/tts_models/en_US-lessac-medium.onnx` in `.env`.

- [ ] **Step 1: Write the failing test**

```python
# tests/tts/test_piper_tts.py
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

def test_synthesize_returns_wav_path(tmp_path):
    with patch("services.tts.piper_tts.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        # Create fake output file so the function doesn't fail
        out = tmp_path / "out.wav"
        out.write_bytes(b"RIFF")

        from services.tts.piper_tts import synthesize
        with patch("services.tts.piper_tts.Path") as MockPath:
            MockPath.return_value = out
            result = synthesize("Hello world", output_path=str(out), model_path="fake.onnx")

        assert result == str(out)

def test_synthesize_raises_on_nonzero_returncode(tmp_path):
    with patch("services.tts.piper_tts.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr=b"error")
        from services.tts.piper_tts import synthesize, TTSError
        with pytest.raises(TTSError):
            synthesize("Hello", output_path=str(tmp_path / "out.wav"), model_path="fake.onnx")
```

- [ ] **Step 2: Run to confirm failure**

```bash
touch tests/tts/__init__.py
PYTHONPATH=. python -m pytest tests/tts/test_piper_tts.py -v
```

- [ ] **Step 3: Implement `services/tts/piper_tts.py`**

```python
# services/tts/piper_tts.py
import subprocess, os
from pathlib import Path

class TTSError(Exception):
    pass

def synthesize(text: str, output_path: str, model_path: str) -> str:
    """
    Run piper TTS to generate a WAV file from text.
    Returns output_path on success, raises TTSError on failure.
    """
    result = subprocess.run(
        ["piper", "--model", model_path, "--output_file", output_path],
        input=text.encode(),
        capture_output=True,
    )
    if result.returncode != 0:
        raise TTSError(f"Piper failed: {result.stderr.decode()}")
    return output_path
```

- [ ] **Step 4: Run tests**

```bash
PYTHONPATH=. python -m pytest tests/tts/test_piper_tts.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/tts/piper_tts.py tests/tts/
git commit -m "feat: piper TTS wrapper"
```

---

## Task 8: Whisper Timestamps

**Files:**
- Create: `services/tts/whisper_timestamps.py`
- Create: `tests/tts/test_whisper_timestamps.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/tts/test_whisper_timestamps.py
from unittest.mock import patch, MagicMock

def test_get_word_timestamps_returns_list_of_dicts():
    mock_segment = MagicMock()
    mock_word = MagicMock()
    mock_word.word = " honey"
    mock_word.start = 0.5
    mock_word.end = 0.9
    mock_segment.words = [mock_word]

    with patch("services.tts.whisper_timestamps.WhisperModel") as MockModel:
        instance = MockModel.return_value
        instance.transcribe.return_value = ([mock_segment], MagicMock())
        from services.tts.whisper_timestamps import get_word_timestamps
        result = get_word_timestamps("fake.wav", model_size="tiny")

    assert result == [{"word": "honey", "start": 0.5, "end": 0.9}]
```

- [ ] **Step 2: Run to confirm failure**

```bash
PYTHONPATH=. python -m pytest tests/tts/test_whisper_timestamps.py -v
```

- [ ] **Step 3: Implement `services/tts/whisper_timestamps.py`**

```python
# services/tts/whisper_timestamps.py
import os
from faster_whisper import WhisperModel

_model = None

def _get_model(model_size: str = "tiny") -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _model

def get_word_timestamps(wav_path: str, model_size: str = "tiny") -> list[dict]:
    """
    Transcribe wav_path with faster-whisper and return word-level timestamps.
    Returns: [{"word": str, "start": float, "end": float}, ...]
    """
    model = _get_model(model_size)
    segments, _ = model.transcribe(wav_path, word_timestamps=True)
    words = []
    for segment in segments:
        for w in segment.words:
            words.append({"word": w.word.strip(), "start": w.start, "end": w.end})
    return words
```

- [ ] **Step 4: Install faster-whisper and run tests**

```bash
pip install faster-whisper
PYTHONPATH=. python -m pytest tests/tts/ -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add services/tts/whisper_timestamps.py tests/tts/test_whisper_timestamps.py
git commit -m "feat: word-level timestamps via faster-whisper"
```

---

## Task 9: TTS Worker Main

**Files:**
- Create: `services/tts/main.py`
- Create: `services/tts/requirements.txt`
- Create: `services/tts/Dockerfile`

- [ ] **Step 1: Implement `services/tts/main.py`**

```python
# services/tts/main.py
import os, json, logging

from services.shared.db import get_conn, init_db
from services.shared.queue import get_queue, enqueue_render
from services.tts.piper_tts import synthesize, TTSError
from services.tts.whisper_timestamps import get_word_timestamps

logging.basicConfig(level=logging.INFO, format="%(asctime)s [tts] %(message)s")
log = logging.getLogger(__name__)

MEDIA_PATH = os.environ.get("MEDIA_PATH", "/media")
MODEL_PATH = os.environ.get("PIPER_MODEL_PATH", "/media/tts_models/en_US-lessac-medium.onnx")

def process_content(content_id: int):
    conn = get_conn()
    init_db(conn)
    row = conn.execute("SELECT * FROM content WHERE id=?", (content_id,)).fetchone()
    if not row:
        log.error(f"Content {content_id} not found")
        return

    audio_dir = os.path.join(MEDIA_PATH, "generated", "audio")
    os.makedirs(audio_dir, exist_ok=True)
    wav_path = os.path.join(audio_dir, f"{content_id}.wav")
    ts_path = os.path.join(audio_dir, f"{content_id}_timestamps.json")

    try:
        synthesize(row["cleaned_script"], wav_path, MODEL_PATH)
        log.info(f"TTS done for content {content_id}")
        timestamps = get_word_timestamps(wav_path)
        with open(ts_path, "w") as f:
            json.dump(timestamps, f)
        conn.execute("UPDATE content SET status='tts_done' WHERE id=?", (content_id,))
        conn.commit()
        q = get_queue("render")
        enqueue_render(q, content_id=content_id)
        log.info(f"Enqueued render for content {content_id}")
    except TTSError as e:
        log.error(f"TTS failed for content {content_id}: {e}")
        conn.execute("UPDATE content SET status='skip' WHERE id=?", (content_id,))
        conn.commit()

if __name__ == "__main__":
    from rq import Worker
    from services.shared.queue import get_redis
    log.info("TTS worker starting")
    worker = Worker(["tts"], connection=get_redis())
    worker.work()
```

- [ ] **Step 2: Create `services/tts/requirements.txt`**

```
faster-whisper==1.0.1
rq==1.16.1
redis==5.0.1
```

Note: Piper TTS binary is installed separately in the Dockerfile.

- [ ] **Step 3: Create `services/tts/Dockerfile`**

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y wget libsndfile1 && rm -rf /var/lib/apt/lists/*
# Install piper binary for ARM64
RUN wget -q https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_aarch64.tar.gz \
    && tar -xzf piper_linux_aarch64.tar.gz -C /usr/local/bin --strip-components=1 \
    && rm piper_linux_aarch64.tar.gz
WORKDIR /app
ENV PYTHONPATH=/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "-m", "services.tts.main"]
```

- [ ] **Step 4: Commit**

```bash
git add services/tts/
git commit -m "feat: TTS worker — Piper + faster-whisper word timestamps"
```

---

## Task 10: Subtitle Generator (ASS format)

**Files:**
- Create: `services/video/subtitles.py`
- Create: `tests/video/test_subtitles.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/video/test_subtitles.py
from services.video.subtitles import timestamps_to_ass, format_ass_time

def test_format_ass_time():
    assert format_ass_time(0.0) == "0:00:00.00"
    assert format_ass_time(61.5) == "0:01:01.50"
    assert format_ass_time(3661.0) == "1:01:01.00"

def test_timestamps_to_ass_contains_header():
    words = [{"word": "Hello", "start": 0.0, "end": 0.5}]
    result = timestamps_to_ass(words)
    assert "[Script Info]" in result
    assert "[V4+ Styles]" in result
    assert "[Events]" in result

def test_timestamps_to_ass_groups_words_into_chunks():
    words = [
        {"word": "Did", "start": 0.0, "end": 0.3},
        {"word": "you", "start": 0.3, "end": 0.6},
        {"word": "know", "start": 0.6, "end": 0.9},
        {"word": "that", "start": 0.9, "end": 1.2},
    ]
    result = timestamps_to_ass(words, words_per_chunk=2)
    # Should produce 2 dialogue lines
    dialogue_lines = [l for l in result.split("\n") if l.startswith("Dialogue:")]
    assert len(dialogue_lines) == 2

def test_timestamps_to_ass_highlights_active_word():
    words = [
        {"word": "Honey", "start": 0.0, "end": 0.5},
        {"word": "never", "start": 0.5, "end": 0.9},
        {"word": "expires", "start": 0.9, "end": 1.4},
    ]
    result = timestamps_to_ass(words, words_per_chunk=3)
    # Active word should use highlight color override
    assert "{\\c&H0020E8&}" in result  # amber color in ASS BGR hex
```

- [ ] **Step 2: Run to confirm failure**

```bash
touch tests/video/__init__.py
PYTHONPATH=. python -m pytest tests/video/test_subtitles.py -v
```

- [ ] **Step 3: Implement `services/video/subtitles.py`**

```python
# services/video/subtitles.py

# ASS color format is BGR hex: #e8a020 (amber) → &H0020A8E8 — but ASS uses AABBGGRR
# #e8a020 in RGB → R=0xe8, G=0xa0, B=0x20 → ASS BGR = &H0020A0E8&
HIGHLIGHT_COLOR = "{\\c&H0020A0E8&}"  # amber
RESET_COLOR = "{\\c&HFFFFFF&}"        # white

def format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

ASS_HEADER = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Syne,72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,0,2,50,50,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def timestamps_to_ass(words: list[dict], words_per_chunk: int = 3) -> str:
    """
    Convert word timestamps to ASS subtitle format.
    Groups words into chunks of words_per_chunk.
    Within each chunk, the currently-speaking word is highlighted in amber.
    """
    if not words:
        return ASS_HEADER

    lines = [ASS_HEADER]

    # Group into chunks
    chunks = [words[i:i+words_per_chunk] for i in range(0, len(words), words_per_chunk)]

    for chunk in chunks:
        chunk_start = chunk[0]["start"]
        chunk_end = chunk[-1]["end"]
        # For each word in chunk, produce one subtitle line where that word is highlighted
        for active_idx, active_word in enumerate(chunk):
            word_start = active_word["start"]
            word_end = active_word["end"]
            # Build text with active word highlighted
            parts = []
            for i, w in enumerate(chunk):
                if i == active_idx:
                    parts.append(f"{HIGHLIGHT_COLOR}{w['word']}{RESET_COLOR}")
                else:
                    parts.append(w["word"])
            text = " ".join(parts)
            lines.append(
                f"Dialogue: 0,{format_ass_time(word_start)},{format_ass_time(word_end)},"
                f"Default,,0,0,0,,{text}"
            )

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests**

```bash
PYTHONPATH=. python -m pytest tests/video/test_subtitles.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add services/video/subtitles.py tests/video/
git commit -m "feat: ASS subtitle generator with word-level amber highlight"
```

---

## Task 11: FFmpeg Renderer

**Files:**
- Create: `services/video/renderer.py`
- Create: `tests/video/test_renderer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/video/test_renderer.py
import os
from unittest.mock import patch, MagicMock
from services.video.renderer import build_ffmpeg_cmd, pick_background_clip

def test_build_ffmpeg_cmd_uses_env_encoder():
    os.environ["VIDEO_ENCODER"] = "libx264"
    cmd = build_ffmpeg_cmd(
        background="/media/bg.mp4",
        audio="/media/audio.wav",
        subtitles="/media/subs.ass",
        output="/media/out.mp4",
        bg_start=10.0,
        duration=45.0,
    )
    assert "libx264" in cmd
    assert "/media/out.mp4" in cmd
    assert "-t" in cmd
    assert "45.0" in cmd

def test_build_ffmpeg_cmd_uses_hw_encoder_when_set():
    os.environ["VIDEO_ENCODER"] = "h264_v4l2m2m"
    cmd = build_ffmpeg_cmd(
        background="/media/bg.mp4",
        audio="/media/audio.wav",
        subtitles="/media/subs.ass",
        output="/media/out.mp4",
        bg_start=10.0,
        duration=45.0,
    )
    assert "h264_v4l2m2m" in cmd

def test_pick_background_clip_returns_file_from_dir(tmp_path):
    (tmp_path / "clip1.mp4").write_bytes(b"")
    (tmp_path / "clip2.mp4").write_bytes(b"")
    result = pick_background_clip(str(tmp_path))
    assert result.endswith(".mp4")
    assert "clip" in result
```

- [ ] **Step 2: Run to confirm failure**

```bash
PYTHONPATH=. python -m pytest tests/video/test_renderer.py -v
```

- [ ] **Step 3: Implement `services/video/renderer.py`**

```python
# services/video/renderer.py
import os, subprocess, random, glob
from pathlib import Path

class RenderError(Exception):
    pass

def pick_background_clip(backgrounds_dir: str) -> str:
    """Pick a random .mp4 file from a directory tree."""
    clips = glob.glob(os.path.join(backgrounds_dir, "**", "*.mp4"), recursive=True)
    if not clips:
        raise RenderError(f"No .mp4 background clips found in {backgrounds_dir}")
    return random.choice(clips)

def build_ffmpeg_cmd(
    background: str,
    audio: str,
    subtitles: str,
    output: str,
    bg_start: float,
    duration: float,
) -> list[str]:
    encoder = os.environ.get("VIDEO_ENCODER", "libx264")
    # Escape subtitles path for ffmpeg filter
    subs_escaped = subtitles.replace(":", "\\:").replace("'", "\\'")

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(bg_start),
        "-i", background,
        "-i", audio,
        "-t", str(duration),
        "-vf", (
            f"scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"ass={subs_escaped}"
        ),
        "-c:v", encoder,
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        output
    ]
    return cmd

def render(
    background: str,
    audio: str,
    subtitles: str,
    output: str,
    duration: float,
) -> str:
    """Render final video. Returns output path on success."""
    # Pick a start offset that leaves room for the full duration
    # We'll use a fixed 10s offset; real clips should be >duration+10s
    bg_start = random.uniform(5, 30)
    cmd = build_ffmpeg_cmd(background, audio, subtitles, output, bg_start, duration)
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RenderError(f"FFmpeg failed: {result.stderr.decode()[-500:]}")
    return output
```

- [ ] **Step 4: Run tests**

```bash
PYTHONPATH=. python -m pytest tests/video/test_renderer.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add services/video/renderer.py tests/video/test_renderer.py
git commit -m "feat: FFmpeg renderer with dual encoder support (libx264/h264_v4l2m2m)"
```

---

## Task 12: Video Worker Main

**Files:**
- Create: `services/video/main.py`
- Create: `services/video/requirements.txt`
- Create: `services/video/Dockerfile`

- [ ] **Step 1: Implement `services/video/main.py`**

```python
# services/video/main.py
import os, json, logging
from pathlib import Path

from services.shared.db import get_conn, init_db
from services.shared.queue import get_redis
from services.video.subtitles import timestamps_to_ass
from services.video.renderer import render, pick_background_clip, RenderError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [video] %(message)s")
log = logging.getLogger(__name__)

MEDIA_PATH = os.environ.get("MEDIA_PATH", "/media")

def get_audio_duration(wav_path: str) -> float:
    """Get duration of WAV using ffprobe."""
    import subprocess, json as _json
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", wav_path],
        capture_output=True
    )
    data = _json.loads(result.stdout)
    return float(data["format"]["duration"])

def process_content(content_id: int):
    conn = get_conn()
    init_db(conn)
    row = conn.execute("SELECT * FROM content WHERE id=?", (content_id,)).fetchone()
    if not row:
        log.error(f"Content {content_id} not found")
        return

    audio_dir = os.path.join(MEDIA_PATH, "generated", "audio")
    video_dir = os.path.join(MEDIA_PATH, "generated", "videos")
    bg_dir    = os.path.join(MEDIA_PATH, "backgrounds")
    os.makedirs(video_dir, exist_ok=True)

    wav_path  = os.path.join(audio_dir, f"{content_id}.wav")
    ts_path   = os.path.join(audio_dir, f"{content_id}_timestamps.json")
    ass_path  = os.path.join(audio_dir, f"{content_id}.ass")
    out_path  = os.path.join(video_dir, f"{content_id}.mp4")

    try:
        with open(ts_path) as f:
            timestamps = json.load(f)
        ass_content = timestamps_to_ass(timestamps)
        with open(ass_path, "w") as f:
            f.write(ass_content)

        duration = get_audio_duration(wav_path)
        background = pick_background_clip(bg_dir)
        render(background, wav_path, ass_path, out_path, duration)

        cur = conn.execute(
            "INSERT INTO videos (content_id, bot_id, audio_path, video_path, duration_secs, status) "
            "VALUES (?,?,?,?,?,'pending_review')",
            (content_id, row["bot_id"], wav_path, out_path, duration)
        )
        conn.commit()
        conn.execute("UPDATE content SET status='rendered' WHERE id=?", (content_id,))
        conn.commit()
        log.info(f"Rendered video for content {content_id} → {out_path}")
    except (RenderError, FileNotFoundError) as e:
        log.error(f"Render failed for content {content_id}: {e}")
        conn.execute("UPDATE content SET status='skip' WHERE id=?", (content_id,))
        conn.commit()

if __name__ == "__main__":
    from rq import Worker
    log.info("Video worker starting")
    worker = Worker(["render"], connection=get_redis())  # type: ignore
    worker.work()
```

- [ ] **Step 2: Create `services/video/requirements.txt`**

```
rq==1.16.1
redis==5.0.1
```

Note: FFmpeg is installed via apt in the Dockerfile.

- [ ] **Step 3: Create `services/video/Dockerfile`**

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV PYTHONPATH=/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "-m", "services.video.main"]
```

- [ ] **Step 4: Add a test background clip for dev**

```bash
# Install yt-dlp once
pip install yt-dlp

# Download a public domain Minecraft video (example — use any long gameplay video)
yt-dlp -f "bestvideo[ext=mp4][height<=1080]" \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  -o "media/backgrounds/gameplay/%(title)s.%(ext)s"
```

- [ ] **Step 5: Commit**

```bash
git add services/video/
git commit -m "feat: video worker — renders MP4 with background + TTS + ASS subtitles"
```

---

## Task 13: FastAPI Backend

**Files:**
- Create: `services/api/main.py`
- Create: `services/api/routers/videos.py`
- Create: `services/api/routers/bots.py`
- Create: `services/api/routers/system.py`
- Create: `services/api/ws.py`
- Create: `tests/api/test_videos.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/api/test_videos.py
import os, pytest
os.environ["DB_PATH"] = ":memory:"
os.environ["MEDIA_PATH"] = "/tmp/bort_test_media"

from fastapi.testclient import TestClient
from services.api.main import app
from services.shared.db import get_conn, init_db

@pytest.fixture(autouse=True)
def setup_db():
    conn = get_conn()
    init_db(conn)
    # Seed a bot and a video
    conn.execute(
        "INSERT INTO bots (name, niche, subreddits, platforms, background_mode, active) "
        "VALUES ('test-bot','facts','[]','[]','random',1)"
    )
    conn.execute(
        "INSERT INTO content (bot_id, reddit_id, subreddit, raw_title, cleaned_script, upvotes, status) "
        "VALUES (1,'abc','todayilearned','TIL test','Did you know test',9999,'rendered')"
    )
    conn.execute(
        "INSERT INTO videos (content_id, bot_id, audio_path, video_path, duration_secs, status) "
        "VALUES (1,1,'/tmp/audio.wav','/tmp/video.mp4',42.0,'pending_review')"
    )
    conn.commit()

client = TestClient(app)

def test_list_pending_videos_returns_200():
    response = client.get("/api/videos?status=pending_review")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "pending_review"

def test_approve_video_changes_status():
    response = client.patch("/api/videos/1/status", json={"status": "approved"})
    assert response.status_code == 200
    check = client.get("/api/videos?status=approved")
    assert len(check.json()) == 1

def test_reject_video_changes_status():
    response = client.patch("/api/videos/1/status", json={"status": "rejected"})
    assert response.status_code == 200
```

- [ ] **Step 2: Run to confirm failure**

```bash
touch tests/api/__init__.py
PYTHONPATH=. python -m pytest tests/api/test_videos.py -v
```

- [ ] **Step 3: Implement `services/api/routers/videos.py`**

```python
# services/api/routers/videos.py
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from services.shared.db import get_conn  # PYTHONPATH=/app makes this work in Docker

router = APIRouter(prefix="/api/videos", tags=["videos"])

class StatusUpdate(BaseModel):
    status: str  # approved | rejected

@router.get("")
def list_videos(status: str = "pending_review"):
    conn = get_conn()
    rows = conn.execute(
        "SELECT v.*, c.cleaned_script, c.subreddit, c.upvotes "
        "FROM videos v JOIN content c ON v.content_id = c.id "
        "WHERE v.status=? ORDER BY v.created_at DESC",
        (status,)
    ).fetchall()
    return [dict(r) for r in rows]

@router.patch("/{video_id}/status")
def update_status(video_id: int, body: StatusUpdate):
    allowed = {"approved", "rejected", "uploading", "uploaded"}
    if body.status not in allowed:
        raise HTTPException(400, f"status must be one of {allowed}")
    conn = get_conn()
    conn.execute("UPDATE videos SET status=? WHERE id=?", (body.status, video_id))
    conn.commit()
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
```

- [ ] **Step 4: Implement `services/api/routers/bots.py`**

```python
# services/api/routers/bots.py
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.shared.db import get_conn

router = APIRouter(prefix="/api/bots", tags=["bots"])

class BotCreate(BaseModel):
    name: str
    niche: str
    subreddits: list[str]
    schedule_cron: str = "0 */6 * * *"
    platforms: list[str] = ["youtube"]
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
    conn = get_conn()
    if body.active is not None:
        conn.execute("UPDATE bots SET active=? WHERE id=?", (int(body.active), bot_id))
    if body.schedule_cron is not None:
        conn.execute("UPDATE bots SET schedule_cron=? WHERE id=?", (body.schedule_cron, bot_id))
    conn.commit()
    return {"ok": True}
```

- [ ] **Step 5: Implement `services/api/routers/system.py`**

```python
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
```

- [ ] **Step 6: Implement `services/api/ws.py`**

```python
# services/api/ws.py
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from services.shared.queue import get_redis
from services.shared.db import get_conn

connected: list[WebSocket] = []

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected.append(websocket)
    try:
        while True:
            # Send status snapshot every 5 seconds
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
```

- [ ] **Step 7: Implement `services/api/main.py`**

```python
# services/api/main.py
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from services.shared.db import get_conn, init_db
from services.api.routers import videos, bots, system
from services.api.ws import websocket_endpoint

app = FastAPI(title="Bort API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tightened to Tailscale domain in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db(get_conn())

app.include_router(videos.router)
app.include_router(bots.router)
app.include_router(system.router)

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket_endpoint(websocket)
```

- [ ] **Step 8: Create `services/api/requirements.txt`**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.1
rq==1.16.1
redis==5.0.1
```

- [ ] **Step 9: Create `services/api/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 10: Install fastapi and run tests**

```bash
pip install fastapi uvicorn httpx pytest-asyncio
PYTHONPATH=. python -m pytest tests/api/test_videos.py -v
```

Expected: all PASS

- [ ] **Step 11: Commit**

```bash
git add services/api/ tests/api/
git commit -m "feat: FastAPI backend — video review, bot management, system status, WebSocket"
```

---

## Task 14: React PWA Scaffold

**Files:**
- Create: `dashboard/package.json`
- Create: `dashboard/vite.config.ts`
- Create: `dashboard/tsconfig.json`
- Create: `dashboard/public/manifest.json`
- Create: `dashboard/src/main.tsx`
- Create: `dashboard/index.html`

- [ ] **Step 1: Scaffold the React app**

```bash
cd dashboard
npm create vite@latest . -- --template react-ts
npm install
npm install react-router-dom
npm install -D vite-plugin-pwa
```

- [ ] **Step 2: Update `dashboard/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'Bort',
        short_name: 'Bort',
        description: 'Content automation dashboard',
        theme_color: '#07080f',
        background_color: '#07080f',
        display: 'standalone',
        orientation: 'portrait',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        runtimeCaching: [
          {
            urlPattern: /^\/api\//,
            handler: 'NetworkFirst',
            options: { cacheName: 'api-cache' },
          },
        ],
      },
    }),
  ],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws':  { target: 'ws://localhost:8000', ws: true },
    },
  },
})
```

- [ ] **Step 3: Create `dashboard/src/api/client.ts`**

```typescript
// dashboard/src/api/client.ts
const BASE = '/api'

export interface Video {
  id: number
  content_id: number
  bot_id: number
  video_path: string
  duration_secs: number
  status: string
  created_at: string
  cleaned_script: string
  subreddit: string
  upvotes: number
}

export interface SystemStatus {
  redis: boolean
  queues: { tts: number; render: number; upload: number }
  counts: { pending_review: number; published_today: number }
}

export async function fetchVideos(status: string): Promise<Video[]> {
  const res = await fetch(`${BASE}/videos?status=${status}`)
  if (!res.ok) throw new Error('Failed to fetch videos')
  return res.json()
}

export async function updateVideoStatus(id: number, status: string): Promise<void> {
  await fetch(`${BASE}/videos/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch(`${BASE}/system/status`)
  return res.json()
}

export function useWebSocket(onMessage: (data: unknown) => void) {
  const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`)
  ws.onmessage = (e) => onMessage(JSON.parse(e.data))
  return ws
}
```

- [ ] **Step 4: Commit**

```bash
cd ..
git add dashboard/
git commit -m "feat: React PWA scaffold with vite-plugin-pwa and API client"
```

---

## Task 15: Dashboard Layout Components

**Files:**
- Create: `dashboard/src/components/Topbar.tsx`
- Create: `dashboard/src/components/Sidebar.tsx`
- Create: `dashboard/src/styles/globals.css`

- [ ] **Step 1: Create `dashboard/src/styles/globals.css`**

```css
/* dashboard/src/styles/globals.css */
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #07080f; --bg2: #0c0e1a; --bg3: #11142b;
  --border: #1c2040; --border2: #252850;
  --text: #e8eaf6; --muted: #5a5f88;
  --accent: #4f7ef7; --accent2: #00c9a7;
  --warn: #e8a020; --danger: #e8404a;
  --font-main: 'DM Sans', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  --font-disp: 'Syne', sans-serif;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-main);
  min-height: 100vh;
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }
```

- [ ] **Step 2: Create `dashboard/src/components/Topbar.tsx`**

```tsx
// dashboard/src/components/Topbar.tsx
import { useEffect, useState } from 'react'
import { fetchSystemStatus, useWebSocket, SystemStatus } from '../api/client'

export function Topbar() {
  const [status, setStatus] = useState<SystemStatus | null>(null)

  useEffect(() => {
    fetchSystemStatus().then(setStatus)
    const ws = useWebSocket((data: any) => {
      if (data.type === 'status') {
        setStatus(prev => prev ? {
          ...prev,
          queues: { ...prev.queues, tts: data.queues.tts, render: data.queues.render },
          counts: { ...prev.counts, pending_review: data.pending_review },
        } : prev)
      }
    })
    return () => ws.close()
  }, [])

  const queueTotal = (status?.queues.tts ?? 0) + (status?.queues.render ?? 0)

  return (
    <header style={{
      display: 'flex', alignItems: 'center', gap: '2rem',
      padding: '0 1.5rem', height: '52px',
      background: 'rgba(7,8,15,0.9)',
      borderBottom: '1px solid var(--border)',
      backdropFilter: 'blur(8px)',
      flexShrink: 0, position: 'sticky', top: 0, zIndex: 100,
    }}>
      <div style={{
        fontFamily: 'var(--font-disp)', fontWeight: 800, fontSize: '1.1rem',
        letterSpacing: '0.12em', color: 'var(--accent)', textTransform: 'uppercase',
        display: 'flex', alignItems: 'center', gap: '0.5rem',
      }}>
        <span style={{
          width: 6, height: 6, borderRadius: '50%', background: 'var(--accent2)',
          animation: 'pulse 2s ease-in-out infinite',
        }} />
        Bort
      </div>
      <div style={{ display: 'flex', gap: '1.5rem', marginLeft: 'auto' }}>
        {[
          { label: 'In Queue',  value: queueTotal,                         color: 'var(--text)' },
          { label: 'Review',    value: status?.counts.pending_review ?? 0, color: 'var(--warn)' },
          { label: 'Published', value: status?.counts.published_today ?? 0,color: 'var(--accent2)' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.62rem', color: 'var(--muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>{label}</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.95rem', fontWeight: 500, color }}>{value}</span>
          </div>
        ))}
      </div>
    </header>
  )
}
```

- [ ] **Step 3: Create `dashboard/src/components/Sidebar.tsx`**

```tsx
// dashboard/src/components/Sidebar.tsx
import { NavLink } from 'react-router-dom'

const NAV = [
  { to: '/',          label: 'Pending' },
  { to: '/published', label: 'Published' },
  { to: '/rejected',  label: 'Rejected' },
  { to: '/settings',  label: 'Settings' },
]

export function Sidebar() {
  return (
    <nav style={{
      width: 200, background: 'var(--bg2)',
      borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column',
      padding: '1.25rem 0', flexShrink: 0,
    }}>
      <Section label="Bots">
        <BotItem name="did-you-know" platforms="YT · TikTok · IG" active />
        <AddBot />
      </Section>
      <Section label="Services">
        {['Scraper','TTS Worker','Video Worker','Upload Worker','Redis'].map(s => (
          <ServiceRow key={s} name={s} up />
        ))}
      </Section>
      <Section label="Navigate">
        {NAV.map(({ to, label }) => (
          <NavLink key={to} to={to} end={to === '/'} style={({ isActive }) => ({
            display: 'block', padding: '0.45rem 0.75rem',
            fontSize: '0.8rem',
            color: isActive ? 'var(--accent)' : 'var(--muted)',
            borderLeft: isActive ? '2px solid var(--accent)' : '2px solid transparent',
            background: isActive ? 'rgba(79,126,247,0.07)' : 'transparent',
            paddingLeft: isActive ? '0.9rem' : '0.75rem',
            borderRadius: '6px', marginBottom: '0.1rem',
            textDecoration: 'none', transition: 'all 0.15s',
          })}>
            {label}
          </NavLink>
        ))}
      </Section>
    </nav>
  )
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ padding: '0 1rem', marginBottom: '1.5rem' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.62rem', fontWeight: 500, color: 'var(--muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.5rem', paddingLeft: '0.25rem' }}>
        {label}
      </div>
      {children}
    </div>
  )
}

function BotItem({ name, platforms, active }: { name: string; platforms: string; active: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.55rem 0.75rem', borderRadius: '6px', background: 'var(--bg3)', border: '1px solid var(--border2)', marginBottom: '0.2rem' }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: active ? 'var(--accent2)' : 'var(--muted)', flexShrink: 0, animation: active ? 'pulse 2s ease-in-out infinite' : 'none' }} />
      <div>
        <div style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--text)' }}>{name}</div>
        <div style={{ fontSize: '0.68rem', color: 'var(--muted)', fontFamily: 'var(--font-mono)' }}>{platforms}</div>
      </div>
    </div>
  )
}

function AddBot() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.45rem 0.75rem', marginTop: '0.2rem', fontSize: '0.75rem', color: 'var(--muted)', cursor: 'pointer', borderRadius: '6px', border: '1px dashed var(--border2)' }}>
      <span>+</span><span>New bot</span>
    </div>
  )
}

function ServiceRow({ name, up }: { name: string; up: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.25rem 0.25rem', fontSize: '0.75rem', color: 'var(--muted)' }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: up ? 'var(--accent2)' : 'var(--danger)', flexShrink: 0 }} />
      {name}
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/
git commit -m "feat: dashboard layout — Topbar with live stats, Sidebar with nav and service status"
```

---

## Task 16: Pending Videos Page + VideoCard

**Files:**
- Create: `dashboard/src/components/VideoCard.tsx`
- Create: `dashboard/src/pages/Pending.tsx`

- [ ] **Step 1: Create `dashboard/src/components/VideoCard.tsx`**

```tsx
// dashboard/src/components/VideoCard.tsx
import { useState } from 'react'
import { Video, updateVideoStatus } from '../api/client'

interface Props {
  video: Video
  onAction: (id: number, status: 'approved' | 'rejected') => void
}

export function VideoCard({ video, onAction }: Props) {
  const [previewing, setPreviewing] = useState(false)

  const age = () => {
    const diff = Date.now() - new Date(video.created_at).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 60) return `${mins}m ago`
    return `${Math.floor(mins / 60)}h ago`
  }

  return (
    <div style={{
      display: 'flex', gap: '1rem', alignItems: 'flex-start',
      background: 'var(--bg2)', border: '1px solid var(--border)',
      borderLeft: '3px solid transparent', borderRadius: '8px',
      padding: '1rem', marginBottom: '0.75rem',
      transition: 'border-color 0.2s, background 0.2s',
    }}
      onMouseEnter={e => (e.currentTarget.style.borderLeftColor = 'var(--accent)')}
      onMouseLeave={e => (e.currentTarget.style.borderLeftColor = 'transparent')}
    >
      {/* Thumbnail */}
      <div style={{
        width: 54, height: 96, flexShrink: 0,
        background: 'var(--bg3)', border: '1px solid var(--border2)',
        borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center',
        cursor: 'pointer',
      }} onClick={() => setPreviewing(v => !v)}>
        <div style={{ width: 0, height: 0, borderLeft: '14px solid var(--accent)', borderTop: '8px solid transparent', borderBottom: '8px solid transparent', opacity: 0.5, marginLeft: 3 }} />
      </div>

      <div style={{ flex: 1 }}>
        <div style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text)', marginBottom: '0.35rem', lineHeight: 1.4 }}>
          {video.cleaned_script.slice(0, 120)}{video.cleaned_script.length > 120 ? '…' : ''}
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--muted)', display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '0.65rem' }}>
          <span>r/{video.subreddit}</span>
          <span>·</span>
          <span>{video.upvotes.toLocaleString()} upvotes</span>
          <span>·</span>
          <span>{Math.round(video.duration_secs)}s</span>
          <span>·</span>
          <span>{age()}</span>
        </div>

        {previewing && (
          <video
            src={`/api/videos/${video.id}/stream`}
            controls autoPlay
            style={{ width: '100%', maxWidth: 300, borderRadius: 6, marginBottom: '0.65rem' }}
          />
        )}

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {[
            { label: 'Approve', status: 'approved' as const, color: 'rgba(0,201,167,0.12)', text: 'var(--accent2)', border: 'rgba(0,201,167,0.3)' },
            { label: 'Reject',  status: 'rejected' as const, color: 'rgba(232,64,74,0.1)',  text: 'var(--danger)', border: 'rgba(232,64,74,0.25)' },
          ].map(({ label, status, color, text, border }) => (
            <button key={label} onClick={() => onAction(video.id, status)} style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.7rem', fontWeight: 500,
              letterSpacing: '0.04em', padding: '0.35rem 0.85rem',
              borderRadius: 5, border: `1px solid ${border}`,
              background: color, color: text, cursor: 'pointer',
              textTransform: 'uppercase',
            }}>
              {label}
            </button>
          ))}
          <button onClick={() => setPreviewing(v => !v)} style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.7rem', fontWeight: 500,
            letterSpacing: '0.04em', padding: '0.35rem 0.85rem',
            borderRadius: 5, border: '1px solid var(--border2)',
            background: 'transparent', color: 'var(--muted)', cursor: 'pointer',
            textTransform: 'uppercase',
          }}>
            {previewing ? 'Hide' : 'Preview'}
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create `dashboard/src/pages/Pending.tsx`**

```tsx
// dashboard/src/pages/Pending.tsx
import { useEffect, useState } from 'react'
import { Video, fetchVideos, updateVideoStatus } from '../api/client'
import { VideoCard } from '../components/VideoCard'

export function Pending() {
  const [videos, setVideos] = useState<Video[]>([])

  useEffect(() => { fetchVideos('pending_review').then(setVideos) }, [])

  const handleAction = async (id: number, status: 'approved' | 'rejected') => {
    await updateVideoStatus(id, status)
    setVideos(vs => vs.filter(v => v.id !== id))
  }

  return (
    <main style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', background: 'var(--bg)' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '1.25rem' }}>
        <span style={{ fontFamily: 'var(--font-disp)', fontSize: '1rem', fontWeight: 700 }}>Pending Review</span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--warn)',
          background: 'rgba(232,160,32,0.1)', border: '1px solid rgba(232,160,32,0.25)',
          padding: '0.15rem 0.5rem', borderRadius: 20,
        }}>
          {videos.length} videos
        </span>
      </div>
      {videos.length === 0 && (
        <p style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>No videos pending review.</p>
      )}
      {videos.map(v => <VideoCard key={v.id} video={v} onAction={handleAction} />)}
    </main>
  )
}
```

- [ ] **Step 3: Create remaining pages**

```tsx
// dashboard/src/pages/Published.tsx
import { useEffect, useState } from 'react'
import { Video, fetchVideos } from '../api/client'
import { VideoCard } from '../components/VideoCard'

export function Published() {
  const [videos, setVideos] = useState<Video[]>([])
  useEffect(() => { fetchVideos('uploaded').then(setVideos) }, [])
  return (
    <main style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', background: 'var(--bg)' }}>
      <div style={{ fontFamily: 'var(--font-disp)', fontSize: '1rem', fontWeight: 700, marginBottom: '1.25rem' }}>Published</div>
      {videos.length === 0 && <p style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>No published videos yet.</p>}
      {videos.map(v => <VideoCard key={v.id} video={v} onAction={() => {}} />)}
    </main>
  )
}
```

```tsx
// dashboard/src/pages/Rejected.tsx
import { useEffect, useState } from 'react'
import { Video, fetchVideos } from '../api/client'
import { VideoCard } from '../components/VideoCard'

export function Rejected() {
  const [videos, setVideos] = useState<Video[]>([])
  useEffect(() => { fetchVideos('rejected').then(setVideos) }, [])
  return (
    <main style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', background: 'var(--bg)' }}>
      <div style={{ fontFamily: 'var(--font-disp)', fontSize: '1rem', fontWeight: 700, marginBottom: '1.25rem' }}>Rejected</div>
      {videos.length === 0 && <p style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>No rejected videos.</p>}
      {videos.map(v => <VideoCard key={v.id} video={v} onAction={() => {}} />)}
    </main>
  )
}
```

```tsx
// dashboard/src/pages/Settings.tsx
export function Settings() {
  return (
    <main style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', background: 'var(--bg)' }}>
      <div style={{ fontFamily: 'var(--font-disp)', fontSize: '1rem', fontWeight: 700, marginBottom: '1.25rem' }}>Settings</div>
      <p style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>Bot configuration — coming in Phase 2.</p>
    </main>
  )
}
```

- [ ] **Step 4: Wire up `dashboard/src/App.tsx`**

```tsx
// dashboard/src/App.tsx
import './styles/globals.css'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Topbar }    from './components/Topbar'
import { Sidebar }   from './components/Sidebar'
import { Pending }   from './pages/Pending'
import { Published } from './pages/Published'
import { Rejected }  from './pages/Rejected'
import { Settings }  from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
        <Topbar />
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          <Sidebar />
          <Routes>
            <Route path="/"           element={<Pending />} />
            <Route path="/published"  element={<Published />} />
            <Route path="/rejected"   element={<Rejected />} />
            <Route path="/settings"   element={<Settings />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}
```

- [ ] **Step 5: Run dev server and verify visually**

```bash
cd dashboard && npm run dev
```

Open http://localhost:5173 — should show the Bort dashboard with sidebar and empty pending queue.

- [ ] **Step 6: Commit**

```bash
cd ..
git add dashboard/src/
git commit -m "feat: dashboard pages — Pending, Published, Rejected, Settings, VideoCard with preview"
```

---

## Task 17: Nginx Config

**Files:**
- Create: `nginx/nginx.conf`
- Create: `nginx/Dockerfile`

- [ ] **Step 1: Create `nginx/nginx.conf`**

```nginx
events { worker_processes 1; }

http {
  include mime.types;
  default_type application/octet-stream;
  sendfile on;
  client_max_body_size 500M;

  upstream api {
    server api:8000;
  }

  server {
    listen 80;
    server_name _;

    # API proxy
    location /api/ {
      proxy_pass http://api/api/;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket proxy
    location /ws {
      proxy_pass http://api/ws;
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "upgrade";
      proxy_set_header Host $host;
    }

    # PWA static files
    location / {
      root /usr/share/nginx/html;
      try_files $uri $uri/ /index.html;
      # Cache static assets, not HTML
      location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
      }
    }
  }
}
```

- [ ] **Step 2: Create `nginx/Dockerfile`**

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY dashboard/package*.json ./
RUN npm ci
COPY dashboard/ .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx/nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

- [ ] **Step 3: Build and test Nginx locally**

```bash
docker compose build nginx
docker compose up nginx api redis -d
curl http://localhost/api/system/status
```

Expected: JSON with redis status and queue counts.

- [ ] **Step 4: Commit**

```bash
git add nginx/
git commit -m "feat: nginx — serves PWA + proxies /api and /ws to FastAPI"
```

---

## Task 18: Production Docker Compose Override

**Files:**
- Create: `docker-compose.prod.yml`

- [ ] **Step 1: Create `docker-compose.prod.yml`**

```yaml
# docker-compose.prod.yml — overlay for RPi5 production
# Usage: docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

services:
  video-worker:
    environment:
      VIDEO_ENCODER: h264_v4l2m2m
    devices:
      - /dev/video0:/dev/video0
      - /dev/video1:/dev/video1

  api:
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2

  ui:
    # In prod, UI is served by nginx (built into the image) — disable the dev server
    profiles: ["dev-only"]

  nginx:
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - /var/lib/tailscale/certs:/certs:ro
      - ./nginx/nginx-prod.conf:/etc/nginx/nginx.conf:ro
```

- [ ] **Step 2: Create `nginx/nginx-prod.conf`** (HTTPS with Tailscale cert)

```nginx
events { worker_processes 1; }

http {
  include mime.types;
  default_type application/octet-stream;
  sendfile on;
  client_max_body_size 500M;

  upstream api { server api:8000; }

  # Redirect HTTP → HTTPS
  server {
    listen 80;
    return 301 https://$host$request_uri;
  }

  server {
    listen 443 ssl;
    server_name bort;  # replace with your tailnet hostname

    ssl_certificate     /certs/bort.crt;
    ssl_certificate_key /certs/bort.key;

    location /api/ {
      proxy_pass http://api/api/;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws {
      proxy_pass http://api/ws;
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "upgrade";
    }

    location / {
      root /usr/share/nginx/html;
      try_files $uri $uri/ /index.html;
      location ~* \.(js|css|png|ico|svg|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
      }
    }
  }
}
```

- [ ] **Step 3: Tailscale HTTPS setup on RPi5 (one-time)**

```bash
# SSH into RPi5 via Tailscale
ssh pi@bort.ts.net

# Enable HTTPS on the Tailscale node
sudo tailscale cert bort.ts.net

# Certs are saved to /var/lib/tailscale/certs/
# docker-compose.prod.yml mounts them into nginx
```

- [ ] **Step 4: Commit**

```bash
git add docker-compose.prod.yml nginx/nginx-prod.conf
git commit -m "feat: production docker-compose override — hw encoder + Tailscale HTTPS"
```

---

## Task 19: End-to-End Smoke Test

Verify the full pipeline runs locally before deploying to RPi5.

- [ ] **Step 1: Copy `.env.example` to `.env` and fill in Reddit credentials**

Register a Reddit app at https://www.reddit.com/prefs/apps (type: script). Add `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` to `.env`.

- [ ] **Step 2: Start all services**

```bash
docker compose up --build -d
docker compose logs -f scraper
```

Expected: `Scraped N new posts` in scraper logs after startup.

- [ ] **Step 3: Verify TTS job runs**

```bash
docker compose logs -f tts-worker
```

Expected: `TTS done for content X` and `Enqueued render for content X`.

- [ ] **Step 4: Verify video renders**

```bash
docker compose logs -f video-worker
```

Expected: `Rendered video for content X → /media/generated/videos/X.mp4`

- [ ] **Step 5: Verify video appears in dashboard**

Open http://localhost (nginx) or http://localhost:5173 (Vite dev).
Expected: At least one video card in "Pending Review" with Approve / Reject / Preview buttons.

- [ ] **Step 6: Approve a video and verify DB status change**

Click Approve. The card should disappear from Pending. In the Published tab it should appear once `status=uploaded` (it will show as `approved` for now — upload worker comes in Phase 2).

- [ ] **Step 7: Run full test suite**

```bash
source .venv/bin/activate
PYTHONPATH=. python -m pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 8: Final commit**

```bash
git add .
git commit -m "chore: phase 1 complete — core pipeline + dashboard smoke tested"
```

---

## Deploy to RPi5

Once the smoke test passes on MacBook:

```bash
# On RPi5 (via Tailscale SSH)
git clone <your-repo-url> ~/bort
cd ~/bort
cp .env.example .env
# Fill in credentials
# Mount HDD at /media and NVMe at /data (or adjust .env paths)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

Install the PWA: open `https://bort.[tailnet].ts.net` in Safari (iOS/Mac) → Share → Add to Home Screen.

---

*Phase 2 plan (YouTube upload integration) is a separate document.*
