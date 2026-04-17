# Gemini expand queue — design spec

**Date:** 2026-04-17

## Problem

When a scraped script is too short for a good video, `expand_script` currently falls back to keyword templates if Gemini is unavailable. The user wants quality Gemini elaborations — not template fallbacks. If Gemini can't be reached (no key or quota exhausted), the content should wait until Gemini is available rather than proceed with a low-quality script.

## Behavior

| Condition | Action |
|-----------|--------|
| Script already ≥ TARGET_WORD_COUNT | Proceed normally → enqueue TTS |
| Script short + Gemini returns elaboration | Expand → enqueue TTS |
| Script short + Gemini unavailable (quota or no key) | `status = expand_pending`, do NOT enqueue TTS |

The template fallback is removed from the main pipeline entirely.

## Schema change

`content.status` gains a new value: **`expand_pending`**.

Full status lifecycle:
```
pending → tts_queued → tts_done → render_queued → rendered → pending_review
                                                              ↓
                                                           skip
expand_pending  (blocked, waiting for Gemini)
```

No structural DB migration needed — SQLite TEXT column, new string value only.

## Components

### `services/scraper/expander.py`

- Remove `expand_script` from the main pipeline (keep it only if referenced by `scripts/regenerate.py`, otherwise delete).
- Add `gemini_available() -> bool`: returns `True` if `GEMINI_API_KEY` env var is set.
- `_gemini_elaborate` already returns `None` on failure — no changes needed there.
- Public API used by the pipeline: `_gemini_elaborate` (called directly) and `gemini_available`.

### `services/scraper/reddit.py`

Replace the `expand_script(clean_til(title))` call with:

```python
script = clean_til(post["title"])
if len(script.split()) >= TARGET_WORD_COUNT:
    cleaned_script = script
    content_status = "pending"
else:
    elaboration = _gemini_elaborate(script)
    if elaboration:
        base = script.rstrip()
        if base and base[-1] not in ".!?":
            base += "."
        cleaned_script = f"{base} {elaboration}"
        content_status = "pending"
    else:
        cleaned_script = script
        content_status = "expand_pending"
```

Insert content with the computed `content_status`. Only enqueue TTS when `content_status == "pending"`.

### `services/scheduler/main.py`

Add a retry function `retry_expand()` that runs every hour:

```python
def retry_expand():
    rows = conn.execute(
        "SELECT id, cleaned_script FROM content WHERE status='expand_pending'"
    ).fetchall()
    for row in rows:
        elaboration = _gemini_elaborate(row["cleaned_script"])
        if elaboration is None:
            break  # quota still exhausted — stop trying this cycle
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
```

The `break` on first failure avoids N redundant Gemini calls when quota is clearly exhausted.

Wire into the scheduler loop via `schedule.every(1).hours.do(retry_expand)`.

### `services/api/routers/system.py`

New endpoint:

```
GET /api/system/gemini-status
→ { "key_missing": bool, "expand_pending_count": int }
```

- `key_missing`: `not bool(os.environ.get("GEMINI_API_KEY"))`
- `expand_pending_count`: `SELECT COUNT(*) FROM content WHERE status='expand_pending'`

### Dashboard

- Nav pills (Queue, Review, Today) each show a count badge when > 0. Add a **Gemini** nav item (or section) that shows `expand_pending_count` as a pill whenever > 0.
- Permanent warning banner visible only when `key_missing = true`: `"⚠ Gemini API key not configured — N videos waiting"`.
- Poll `/api/system/gemini-status` at the same interval as the existing system health polling.

## What does NOT change

- `expand_script` with template fallback is kept intact for `scripts/regenerate.py` — only removed from the scraper pipeline.
- `services/tts/main.py` — no changes.
- `services/video/main.py` — no changes.
- All existing tests pass without modification.

## Out of scope

- Manual retry button in the dashboard.
- Per-item retry or skip for `expand_pending` content.
- Notifications/push for when Gemini comes back online.
