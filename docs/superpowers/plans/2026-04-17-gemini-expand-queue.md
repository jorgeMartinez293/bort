# Gemini Expand Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hold short scripts in `expand_pending` status when Gemini is unavailable instead of falling back to keyword templates, retrying every hour via the scheduler, and surfacing a count pill + optional warning in the dashboard.

**Architecture:** `reddit.py` classifies each post as `pending` (long enough or Gemini elaborated) or `expand_pending` (short + Gemini failed). The scheduler gains an hourly `retry_expand()` that promotes `expand_pending` rows. A new `/api/system/gemini-status` endpoint exposes `key_missing` and `expand_pending_count` to the dashboard Sidebar.

**Tech Stack:** Python 3.12, FastAPI, SQLite, RQ/Redis, React 19 + TypeScript

---

### Task 1: Extend expander.py with public helpers

**Files:**
- Modify: `services/scraper/expander.py`
- Test: `tests/scraper/test_expander.py` (new file)

- [ ] **Step 1: Write failing tests**

```python
# tests/scraper/test_expander.py
import os
from unittest.mock import patch
from services.scraper.expander import gemini_available, gemini_elaborate_or_none

def test_gemini_available_false_when_no_key():
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("GEMINI_API_KEY", None)
        assert gemini_available() is False

def test_gemini_available_true_when_key_set():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        assert gemini_available() is True

def test_gemini_elaborate_or_none_returns_none_when_no_key():
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("GEMINI_API_KEY", None)
        result = gemini_elaborate_or_none("Honey never expires.")
        assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. python3 -m pytest tests/scraper/test_expander.py -v
```
Expected: FAIL with `ImportError` (functions don't exist yet)

- [ ] **Step 3: Add the two public functions to expander.py**

At the bottom of `services/scraper/expander.py`, after the existing `expand_script` function, add:

```python
def gemini_available() -> bool:
    """True if GEMINI_API_KEY is set in the environment."""
    return bool(os.environ.get("GEMINI_API_KEY"))


def gemini_elaborate_or_none(script: str) -> Optional[str]:
    """Return a Gemini elaboration or None if unavailable/quota exceeded."""
    return _gemini_elaborate(script)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. python3 -m pytest tests/scraper/test_expander.py -v
```
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add services/scraper/expander.py tests/scraper/test_expander.py
git commit -m "feat: add gemini_available and gemini_elaborate_or_none to expander"
```

---

### Task 2: Update reddit.py to emit status field

**Files:**
- Modify: `services/scraper/reddit.py`
- Modify: `tests/scraper/test_reddit.py`

- [ ] **Step 1: Update existing tests and add new ones**

Replace the contents of `tests/scraper/test_reddit.py`:

```python
from unittest.mock import patch, MagicMock
from services.scraper.reddit import fetch_posts


def _make_response(posts_data):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "data": {"children": [{"data": p} for p in posts_data]}
    }
    mock_resp.raise_for_status.return_value = None
    return mock_resp


def test_fetch_posts_long_script_is_pending_without_gemini():
    """A script already >= TARGET_WORD_COUNT words gets status 'pending' with no Gemini call."""
    long_title = "TIL " + " ".join(["word"] * 30)
    posts_data = [
        {"id": "aaa", "title": long_title, "score": 50_000,
         "subreddit": "todayilearned", "stickied": False},
    ]
    with patch("services.scraper.reddit.requests.get") as mock_get:
        mock_get.return_value = _make_response(posts_data)
        with patch("services.scraper.reddit.gemini_elaborate_or_none", return_value=None) as mock_gem:
            posts = fetch_posts(subreddit="todayilearned", limit=10, seen_ids=set())
    assert len(posts) == 1
    assert posts[0]["status"] == "pending"
    mock_gem.assert_not_called()


def test_fetch_posts_short_script_with_gemini_is_pending():
    """A short script expanded by Gemini gets status 'pending'."""
    posts_data = [
        {"id": "aaa", "title": "TIL that honey never expires.", "score": 50_000,
         "subreddit": "todayilearned", "stickied": False},
    ]
    elaboration = "This happens because honey is a natural preservative with low moisture."
    with patch("services.scraper.reddit.requests.get") as mock_get:
        mock_get.return_value = _make_response(posts_data)
        with patch("services.scraper.reddit.gemini_elaborate_or_none", return_value=elaboration):
            posts = fetch_posts(subreddit="todayilearned", limit=10, seen_ids=set())
    assert len(posts) == 1
    assert posts[0]["status"] == "pending"
    assert posts[0]["cleaned_script"].startswith("Did you know")
    assert elaboration in posts[0]["cleaned_script"]


def test_fetch_posts_short_script_without_gemini_is_expand_pending():
    """A short script where Gemini fails gets status 'expand_pending' and no elaboration."""
    posts_data = [
        {"id": "bbb", "title": "TIL octopuses have three hearts", "score": 25_000,
         "subreddit": "todayilearned", "stickied": False},
    ]
    with patch("services.scraper.reddit.requests.get") as mock_get:
        mock_get.return_value = _make_response(posts_data)
        with patch("services.scraper.reddit.gemini_elaborate_or_none", return_value=None):
            posts = fetch_posts(subreddit="todayilearned", limit=10, seen_ids=set())
    assert len(posts) == 1
    assert posts[0]["status"] == "expand_pending"
    assert posts[0]["cleaned_script"].startswith("Did you know")


def test_fetch_posts_skips_seen_ids():
    posts_data = [
        {"id": "aaa", "title": "TIL that honey never expires.", "score": 50_000,
         "subreddit": "todayilearned", "stickied": False},
    ]
    with patch("services.scraper.reddit.requests.get") as mock_get:
        mock_get.return_value = _make_response(posts_data)
        posts = fetch_posts(subreddit="todayilearned", limit=10, seen_ids={"aaa"})
    assert posts == []


def test_fetch_posts_skips_stickied():
    posts_data = [
        {"id": "aaa", "title": "TIL that honey never expires.", "score": 50_000,
         "subreddit": "todayilearned", "stickied": True},
        {"id": "bbb", "title": "TIL octopuses have three hearts", "score": 25_000,
         "subreddit": "todayilearned", "stickied": False},
    ]
    with patch("services.scraper.reddit.requests.get") as mock_get, \
         patch("services.scraper.reddit.gemini_elaborate_or_none", return_value=None):
        mock_get.return_value = _make_response(posts_data)
        posts = fetch_posts(subreddit="todayilearned", limit=10, seen_ids=set())
    assert len(posts) == 1
    assert posts[0]["reddit_id"] == "bbb"
```

- [ ] **Step 2: Run tests to verify the new ones fail**

```bash
PYTHONPATH=. python3 -m pytest tests/scraper/test_reddit.py -v
```
Expected: new tests FAIL (old behavior still in place)

- [ ] **Step 3: Rewrite reddit.py with new expansion logic**

Replace the full contents of `services/scraper/reddit.py`:

```python
import os
import requests
from services.scraper.cleaner import clean_til, is_suitable
from services.scraper.expander import gemini_elaborate_or_none, TARGET_WORD_COUNT

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def _extract_image_url(post: dict) -> "str | None":
    if post.get("post_hint") != "image":
        return None
    url = post.get("url", "")
    ext = os.path.splitext(url.lower().split("?")[0])[1]
    return url if ext in _IMAGE_EXTS else None


def fetch_posts(
    subreddit: str,
    limit: int,
    seen_ids: set,
    user_agent: str = "bort/0.1",
) -> list:
    """Fetch hot posts from a subreddit via the public Reddit JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json"
    response = requests.get(
        url,
        params={"limit": limit},
        headers={"User-Agent": user_agent},
        timeout=10,
    )
    response.raise_for_status()
    children = response.json()["data"]["children"]
    results = []
    for child in children:
        post = child["data"]
        if post.get("stickied"):
            continue
        if not is_suitable(post["score"], post["id"], seen_ids):
            continue

        script = clean_til(post["title"])
        if len(script.split()) >= TARGET_WORD_COUNT:
            cleaned_script = script
            status = "pending"
        else:
            elaboration = gemini_elaborate_or_none(script)
            if elaboration:
                base = script.rstrip()
                if base and base[-1] not in ".!?":
                    base += "."
                cleaned_script = f"{base} {elaboration}"
                status = "pending"
            else:
                cleaned_script = script
                status = "expand_pending"

        results.append({
            "reddit_id": post["id"],
            "subreddit": post["subreddit"],
            "raw_title": post["title"],
            "cleaned_script": cleaned_script,
            "upvotes": post["score"],
            "image_url": _extract_image_url(post),
            "status": status,
        })
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. python3 -m pytest tests/scraper/test_reddit.py -v
```
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add services/scraper/reddit.py tests/scraper/test_reddit.py
git commit -m "feat: reddit.py emits status field, expand_pending when Gemini unavailable"
```

---

### Task 3: Update scraper/main.py to use dynamic status

**Files:**
- Modify: `services/scraper/main.py`

No new tests needed — the scraper main is integration-level and the logic change is trivial (use a field already tested in Task 2).

- [ ] **Step 1: Update the INSERT and conditional enqueue in scraper/main.py**

Replace these lines in `run_scrape()`:

```python
# OLD
cur = conn.execute(
    "INSERT INTO content (bot_id, reddit_id, subreddit, raw_title, cleaned_script, upvotes, status, image_url) "
    "VALUES (?,?,?,?,?,?,'pending',?)",
    (BOT_ID, post["reddit_id"], post["subreddit"], post["raw_title"], post["cleaned_script"], post["upvotes"], post.get("image_url"))
)
conn.commit()
assert cur.lastrowid is not None
enqueue_tts(q, content_id=cur.lastrowid)
```

With:

```python
# NEW
cur = conn.execute(
    "INSERT INTO content (bot_id, reddit_id, subreddit, raw_title, cleaned_script, upvotes, status, image_url) "
    "VALUES (?,?,?,?,?,?,?,?)",
    (BOT_ID, post["reddit_id"], post["subreddit"], post["raw_title"], post["cleaned_script"], post["upvotes"], post["status"], post.get("image_url"))
)
conn.commit()
assert cur.lastrowid is not None
if post["status"] == "pending":
    enqueue_tts(q, content_id=cur.lastrowid)
```

- [ ] **Step 2: Run full test suite to verify nothing broke**

```bash
PYTHONPATH=. python3 -m pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add services/scraper/main.py
git commit -m "feat: scraper uses dynamic content status and skips TTS enqueue for expand_pending"
```

---

### Task 4: Add hourly retry_expand to scheduler

**Files:**
- Modify: `services/scheduler/main.py`
- Test: `tests/scheduler/test_retry_expand.py` (new file — create `tests/scheduler/__init__.py` too)

- [ ] **Step 1: Write failing tests**

```bash
mkdir -p tests/scheduler && touch tests/scheduler/__init__.py
```

```python
# tests/scheduler/test_retry_expand.py
from unittest.mock import MagicMock, patch
from services.scheduler.main import retry_expand


def test_retry_expand_expands_and_enqueues_on_gemini_success():
    rows = [{"id": 7, "cleaned_script": "Did you know bees dance."}]
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = rows
    mock_q = MagicMock()
    elaboration = "This happens because bees use waggle dances to communicate direction."

    with patch("services.scheduler.main.gemini_elaborate_or_none", return_value=elaboration), \
         patch("services.scheduler.main.enqueue_tts") as mock_enqueue:
        retry_expand(conn, mock_q)

    mock_enqueue.assert_called_once_with(mock_q, content_id=7)
    conn.commit.assert_called_once()


def test_retry_expand_breaks_on_first_gemini_failure():
    rows = [
        {"id": 1, "cleaned_script": "Short script one."},
        {"id": 2, "cleaned_script": "Short script two."},
    ]
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = rows
    mock_q = MagicMock()

    with patch("services.scheduler.main.gemini_elaborate_or_none", return_value=None), \
         patch("services.scheduler.main.enqueue_tts") as mock_enqueue:
        retry_expand(conn, mock_q)

    mock_enqueue.assert_not_called()
    conn.commit.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. python3 -m pytest tests/scheduler/test_retry_expand.py -v
```
Expected: FAIL (`retry_expand` not found)

- [ ] **Step 3: Update scheduler/main.py**

Replace the full contents of `services/scheduler/main.py`:

```python
import time
import datetime
import logging
from typing import Optional
from services.shared.db import get_conn
from services.shared.queue import get_queue, enqueue_upload, enqueue_tts
from services.scraper.expander import gemini_elaborate_or_none

logging.basicConfig(level=logging.INFO, format="%(asctime)s [scheduler] %(message)s")
log = logging.getLogger(__name__)

INTERVALS = {
    "hourly":   3600,
    "every_6h": 21600,
    "daily":    86400,
}

def _now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _parse_ts(ts: str) -> datetime.datetime:
    dt = datetime.datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def retry_expand(conn, q) -> None:
    """Try to expand all expand_pending content. Stops on first Gemini failure."""
    rows = conn.execute(
        "SELECT id, cleaned_script FROM content WHERE status='expand_pending'"
    ).fetchall()
    for row in rows:
        elaboration = gemini_elaborate_or_none(row["cleaned_script"])
        if elaboration is None:
            break
        base = row["cleaned_script"].rstrip()
        if base and base[-1] not in ".!?":
            base += "."
        expanded = f"{base} {elaboration}"
        conn.execute(
            "UPDATE content SET cleaned_script=?, status='pending' WHERE id=?",
            (expanded, row["id"])
        )
        conn.commit()
        enqueue_tts(q, content_id=row["id"])
        log.info("Expanded and enqueued content %d", row["id"])


def tick(conn, q) -> None:
    bots = conn.execute("SELECT * FROM bots WHERE active=1").fetchall()

    for bot in bots:
        schedule = bot["upload_schedule"]
        if schedule not in INTERVALS:
            continue

        interval_secs = INTERVALS[schedule]
        bot_id = bot["id"]

        in_progress = conn.execute(
            "SELECT COUNT(*) FROM videos WHERE bot_id=? AND status='uploading'",
            (bot_id,)
        ).fetchone()[0]
        if in_progress:
            continue

        row = conn.execute(
            "SELECT MAX(u.published_at) as last_pub FROM uploads u "
            "JOIN videos v ON u.video_id = v.id "
            "WHERE v.bot_id=? AND u.status='done'",
            (bot_id,)
        ).fetchone()

        last_pub = row["last_pub"]
        if last_pub:
            elapsed = (_now_utc() - _parse_ts(last_pub)).total_seconds()
            if elapsed < interval_secs:
                continue

        video = conn.execute(
            "SELECT id FROM videos WHERE bot_id=? AND status='approved' "
            "ORDER BY created_at ASC LIMIT 1",
            (bot_id,)
        ).fetchone()
        if not video:
            continue

        video_id = video["id"]
        conn.execute("UPDATE videos SET status='uploading' WHERE id=?", (video_id,))
        conn.execute(
            "INSERT INTO uploads (video_id, platform, status) VALUES (?, 'youtube', 'pending')",
            (video_id,)
        )
        conn.commit()
        enqueue_upload(q, video_id=video_id)
        log.info("Dispatched video %d for bot %d (schedule: %s)", video_id, bot_id, schedule)


if __name__ == "__main__":
    log.info("Scheduler started")
    conn = get_conn()
    upload_q = get_queue("upload")
    tts_q = get_queue("tts")
    last_expand: Optional[datetime.datetime] = None

    while True:
        try:
            tick(conn, upload_q)
        except Exception as e:
            log.error("Tick error: %s", e)

        now = _now_utc()
        if last_expand is None or (now - last_expand).total_seconds() >= 3600:
            last_expand = now
            try:
                retry_expand(conn, tts_q)
            except Exception as e:
                log.error("retry_expand error: %s", e)

        time.sleep(60)
```

Note: `tick()` now takes `conn` and `q` as parameters instead of creating them internally — this makes it testable and aligns with `retry_expand`'s signature.

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. python3 -m pytest tests/scheduler/test_retry_expand.py -v
```
Expected: 2 PASS

- [ ] **Step 5: Run full suite**

```bash
PYTHONPATH=. python3 -m pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add services/scheduler/main.py tests/scheduler/__init__.py tests/scheduler/test_retry_expand.py
git commit -m "feat: scheduler retries expand_pending content hourly via Gemini"
```

---

### Task 5: Add /api/system/gemini-status endpoint

**Files:**
- Modify: `services/api/routers/system.py`
- Test: `tests/api/test_system.py` (new file)

- [ ] **Step 1: Write failing test**

```python
# tests/api/test_system.py
import os
os.environ["DB_PATH"] = ":memory:"
os.environ["MEDIA_PATH"] = "/tmp/bort_test_media"

import pytest
from fastapi.testclient import TestClient
from services.api.main import app
from services.shared.db import get_conn, init_db, reset_conn

@pytest.fixture(autouse=True)
def setup_db():
    reset_conn()
    conn = get_conn()
    init_db(conn)
    conn.execute(
        "INSERT INTO bots (name, niche, subreddits, platforms, background_mode, active) "
        "VALUES ('test-bot','facts','[]','[]','random',1)"
    )
    conn.commit()

client = TestClient(app)


def test_gemini_status_key_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    conn = get_conn()
    conn.execute(
        "INSERT INTO content (bot_id, reddit_id, subreddit, raw_title, cleaned_script, upvotes, status) "
        "VALUES (1,'abc','todayilearned','TIL test','short',999,'expand_pending')"
    )
    conn.commit()
    resp = client.get("/api/system/gemini-status")
    assert resp.status_code == 200
    assert resp.json()["key_missing"] is True
    assert resp.json()["expand_pending_count"] == 1


def test_gemini_status_key_present(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    resp = client.get("/api/system/gemini-status")
    assert resp.status_code == 200
    assert resp.json()["key_missing"] is False
    assert resp.json()["expand_pending_count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
PYTHONPATH=. python3 -m pytest tests/api/test_system.py -v
```
Expected: FAIL (endpoint doesn't exist)

- [ ] **Step 3: Add the endpoint to system.py**

Add to `services/api/routers/system.py` after the existing `system_status` route:

```python
@router.get("/gemini-status")
def gemini_status():
    conn = get_conn()
    return {
        "key_missing": not bool(os.environ.get("GEMINI_API_KEY")),
        "expand_pending_count": conn.execute(
            "SELECT COUNT(*) FROM content WHERE status='expand_pending'"
        ).fetchone()[0],
    }
```

Also add `import os` at the top of the file.

- [ ] **Step 4: Run test to verify it passes**

```bash
PYTHONPATH=. python3 -m pytest tests/api/test_system.py -v
```
Expected: 2 PASS

- [ ] **Step 5: Run full suite**

```bash
PYTHONPATH=. python3 -m pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add services/api/routers/system.py tests/api/test_system.py
git commit -m "feat: add GET /api/system/gemini-status endpoint"
```

---

### Task 6: Update dashboard API client

**Files:**
- Modify: `dashboard/src/api/client.ts`

No unit tests — frontend API layer is covered by integration.

- [ ] **Step 1: Add GeminiStatus interface and fetchGeminiStatus to client.ts**

Add after the existing `SystemStatus` interface:

```typescript
export interface GeminiStatus {
  key_missing: boolean
  expand_pending_count: number
}
```

Add after the existing `fetchSystemStatus` function:

```typescript
export async function fetchGeminiStatus(): Promise<GeminiStatus> {
  const res = await fetch(`${BASE}/system/gemini-status`)
  return res.json()
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/api/client.ts
git commit -m "feat: add GeminiStatus type and fetchGeminiStatus to dashboard API client"
```

---

### Task 7: Update Sidebar — Waiting pill and key_missing banner

**Files:**
- Modify: `dashboard/src/components/Sidebar.tsx`

- [ ] **Step 1: Update Sidebar.tsx**

Replace the full contents of `dashboard/src/components/Sidebar.tsx`:

```tsx
// dashboard/src/components/Sidebar.tsx
import { useEffect, useRef, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { fetchBots, fetchGeminiStatus } from '../api/client'
import type { Bot, GeminiStatus } from '../api/client'

const NAV = [
  { to: '/',          label: 'Review' },
  { to: '/queue',     label: 'Queue' },
  { to: '/published', label: 'Published' },
  { to: '/rejected',  label: 'Rejected' },
  { to: '/settings',  label: 'Settings' },
]

export function Sidebar() {
  const [bots, setBots] = useState<Bot[]>([])
  const [open, setOpen] = useState(false)
  const [gemini, setGemini] = useState<GeminiStatus>({ key_missing: false, expand_pending_count: 0 })
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchBots().then(setBots).catch(() => {})
  }, [])

  useEffect(() => {
    function poll() {
      fetchGeminiStatus().then(setGemini).catch(() => {})
    }
    poll()
    const id = setInterval(poll, 30_000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    if (!open) return
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  const activeBot = bots.find(b => b.active === 1) ?? bots[0]

  return (
    <nav style={{
      width: 200,
      alignSelf: 'stretch',
      flexShrink: 0,
      display: 'flex',
      flexDirection: 'column',
      padding: '1.5rem 0.75rem',
      background: 'rgba(255,255,255,0.04)',
      backdropFilter: 'blur(16px)',
      WebkitBackdropFilter: 'blur(16px)',
      borderRight: '1px solid rgba(255,255,255,0.08)',
    }}>
      {/* Logo */}
      <div style={{
        fontFamily: 'var(--font-body)',
        fontWeight: 700,
        fontSize: '1.2rem',
        letterSpacing: '-0.03em',
        color: 'var(--violet-light)',
        marginBottom: '1.25rem',
      }}>
        bort
      </div>

      {/* Gemini warning — only when API key is missing */}
      {gemini.key_missing && (
        <div style={{
          marginBottom: '1rem',
          padding: '0.45rem 0.6rem',
          borderRadius: 7,
          background: 'rgba(251,191,36,0.08)',
          border: '1px solid rgba(251,191,36,0.25)',
          fontSize: '0.72rem',
          color: '#fbbf24',
          lineHeight: 1.4,
        }}>
          ⚠ Gemini API key not configured
        </div>
      )}

      {/* Nav pills */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
        {NAV.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.55rem 0.75rem',
              borderRadius: 8,
              fontSize: '0.82rem',
              fontWeight: 500,
              textDecoration: 'none',
              transition: 'all 0.18s',
              background: isActive ? 'var(--glass-bg-active)' : 'transparent',
              border: isActive
                ? '1px solid var(--glass-border-active)'
                : '1px solid transparent',
              color: isActive ? '#c4b5fd' : 'var(--text-muted)',
            })}
          >
            {({ isActive }) => (
              <>
                <span style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: 'var(--violet)',
                  flexShrink: 0,
                  opacity: isActive ? 1 : 0,
                  transition: 'opacity 0.18s',
                }} />
                <span style={{ flex: 1 }}>{label}</span>
              </>
            )}
          </NavLink>
        ))}

        {/* Waiting pill — visible whenever expand_pending_count > 0 */}
        {gemini.expand_pending_count > 0 && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.55rem 0.75rem',
            borderRadius: 8,
            fontSize: '0.82rem',
            fontWeight: 500,
            color: 'var(--text-muted)',
            border: '1px solid transparent',
          }}>
            <span style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: 'transparent',
              flexShrink: 0,
            }} />
            <span style={{ flex: 1 }}>Waiting</span>
            <span style={{
              fontSize: '0.68rem',
              fontWeight: 600,
              padding: '0.1rem 0.4rem',
              borderRadius: 10,
              background: 'rgba(251,191,36,0.15)',
              color: '#fbbf24',
              border: '1px solid rgba(251,191,36,0.3)',
            }}>
              {gemini.expand_pending_count}
            </span>
          </div>
        )}
      </div>

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Bot selector */}
      <div ref={ref} style={{ position: 'relative' }}>
        {open && (
          <div style={{
            position: 'absolute',
            bottom: 'calc(100% + 8px)',
            left: 0,
            right: 0,
            background: 'rgba(15,10,30,0.92)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            border: '1px solid var(--glass-border)',
            borderRadius: 10,
            overflow: 'hidden',
            zIndex: 50,
          }}>
            {bots.map(bot => (
              <div
                key={bot.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.55rem 0.75rem',
                  fontSize: '0.78rem',
                  color: bot.active === 1 ? 'var(--text)' : 'var(--text-muted)',
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={e => (e.currentTarget.style.background = 'rgba(139,92,246,0.1)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <span style={{
                  width: 5,
                  height: 5,
                  borderRadius: '50%',
                  background: bot.active === 1 ? 'var(--emerald)' : 'var(--text-muted)',
                  flexShrink: 0,
                  animation: bot.active === 1 ? 'pulse 2s ease-in-out infinite' : 'none',
                }} />
                {bot.name}
              </div>
            ))}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.55rem 0.75rem',
                fontSize: '0.78rem',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                borderTop: '1px dashed rgba(255,255,255,0.08)',
                transition: 'background 0.15s',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <span style={{ fontSize: '0.9rem', lineHeight: 1 }}>+</span>
              New bot
            </div>
          </div>
        )}

        <button
          onClick={() => setOpen(v => !v)}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.55rem 0.75rem',
            background: 'var(--glass-bg)',
            border: '1px solid var(--glass-border)',
            borderRadius: 8,
            color: 'var(--text)',
            fontSize: '0.78rem',
            fontWeight: 500,
            fontFamily: 'var(--font-body)',
            cursor: 'pointer',
            textAlign: 'left',
            transition: 'background 0.18s',
          }}
        >
          <span style={{
            width: 5,
            height: 5,
            borderRadius: '50%',
            background: 'var(--emerald)',
            flexShrink: 0,
            animation: 'pulse 2s ease-in-out infinite',
          }} />
          <span style={{
            flex: 1,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}>
            {activeBot?.name ?? 'No bots'}
          </span>
          <span style={{
            fontSize: '0.65rem',
            color: 'var(--text-muted)',
            display: 'inline-block',
            transform: open ? 'rotate(180deg)' : 'none',
            transition: 'transform 0.18s',
          }}>▾</span>
        </button>
      </div>
    </nav>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd dashboard && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/Sidebar.tsx
git commit -m "feat: sidebar shows Waiting pill and Gemini key missing warning"
```
