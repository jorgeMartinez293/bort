# Bort — Content Automation System Design

**Date:** 2026-04-14  
**Status:** Approved  
**Author:** Jorge + Claude

---

## Context

The goal is to build a system that automatically generates short-form video content (YouTube Shorts, TikTok, Instagram Reels) with minimal upfront investment. Content is sourced from Reddit (r/todayilearned, r/interestingasfuck), converted to video via TTS + subtitle + background video pipeline, reviewed by the user via a web dashboard, and uploaded to platforms.

The system runs entirely on a Raspberry Pi 5 (8 GB RAM, 1 TB HDD + NVMe), is developed on a MacBook M4 Pro, and deployed via Docker Compose. Both machines are ARM64, so images are fully portable.

---

## Architecture

### Approach: Microservices on RPi5 via Docker Compose

All services run as Docker containers orchestrated by Docker Compose. Each service is independently restartable. Redis decouples pipeline stages. SQLite stores state on the NVMe. Media (gameplay clips, generated videos) lives on the HDD.

```
Reddit API
    ↓ (every 6h)
[Scraper Service]  →  Redis: content:pending
    ↓
[TTS Worker]       →  Redis: video:pending       → WAV + timestamps on HDD
    ↓
[Video Worker]     →  Redis: upload:pending      → MP4 1080×1920 on HDD
    ↓
[Dashboard]        →  User reviews, approves/rejects
    ↓
[Upload Worker]    →  YouTube (Phase 1) / TikTok + IG (Phase 2)
```

### Services

| Service | Image base | Responsibility |
|---|---|---|
| `redis` | redis:7-alpine | Job queue between pipeline stages |
| `scraper` | python:3.12-slim | Fetch Reddit posts via PRAW every 6h; push to content:pending |
| `tts-worker` | python:3.12-slim + Piper | Generate WAV + word-level timestamps from script |
| `video-worker` | python:3.12-slim + FFmpeg | Render final MP4 from audio + background + subtitles |
| `upload-worker` | python:3.12-slim + Playwright | Upload approved videos to platforms |
| `api` | python:3.12-slim | FastAPI REST + WebSocket backend for dashboard |
| `ui` | node:20-alpine / nginx:alpine | PWA — React + Vite (dev) / Nginx serving static build + reverse proxy (prod) |

---

## Storage Layout

```
NVMe (fast, OS + app):
  /app/               ← application code (bind-mounted in dev)
  /data/db/           ← SQLite database file
  /data/redis/        ← Redis persistence

HDD 1TB (media):
  /media/backgrounds/
    gameplay/         ← Minecraft, Subway Surfers clips (downloaded once via yt-dlp)
    images/           ← Pexels/Pixabay stock images
  /media/generated/
    audio/            ← TTS WAV files
    videos/           ← Final MP4 files (pending review + approved)
  /media/archive/     ← Uploaded videos moved here for reference
```

---

## Data Model (SQLite)

```sql
bots (
  id, name, niche,
  subreddits TEXT,      -- JSON array: ["todayilearned", "interestingasfuck"]
  schedule_cron TEXT,   -- e.g. "0 */6 * * *"
  platforms TEXT,       -- JSON array: ["youtube", "tiktok"]
  background_mode TEXT, -- "gameplay" | "images" | "random"
  active BOOLEAN,
  created_at TIMESTAMP
)

content (
  id, bot_id, reddit_id,
  subreddit, raw_title, cleaned_script,
  upvotes INTEGER,
  status TEXT,  -- pending | scripted | tts_done | rendered | skip
  created_at TIMESTAMP
)

videos (
  id, content_id, bot_id,
  audio_path, video_path,
  duration_secs REAL,
  status TEXT,  -- pending_review | approved | rejected | uploading | uploaded
  created_at TIMESTAMP
)

uploads (
  id, video_id, platform,
  status TEXT,           -- pending | uploading | done | failed
  platform_video_id TEXT,
  published_at TIMESTAMP,
  error_msg TEXT
)
```

---

## Video Generation Pipeline

1. **Script cleaning** — Strip "TIL that", clean markdown, add hook ("Did you know...") and CTA ("Follow for more"). Max 150 words → 30–60 s video.

2. **Piper TTS** — Generate WAV audio + JSON word-level timestamps. Runs locally on ARM64. No API cost, no latency.

3. **Subtitle generation** — Convert Piper timestamps to ASS/SRT format. Style: 2–3 words per block, active word highlighted in amber (`#e8a020`), white Syne Bold text with black stroke.

4. **FFmpeg render**:
   - Select random segment from background clip on HDD
   - Overlay TTS audio
   - Burn subtitles with `subtitles` filter
   - Output: 1080×1920, H.264, AAC
   - **Encoder**: `libx264` on MacBook (dev), `h264_v4l2m2m` on RPi5 (hw accel via `devices: [/dev/video0]` in compose)
   - Controlled by env var `VIDEO_ENCODER`

5. **Output**: ~5–15 MB MP4 saved to HDD, DB record set to `pending_review`.

---

## Dashboard App

**Architecture:** The dashboard is a standalone PWA (Progressive Web App) — a separate client that connects to the RPi5 API. It is served as static files by Nginx on the RPi5 and installable on any device (Mac, iPhone, Android) directly from the browser, with no App Store required.

**Stack:** FastAPI (backend API + WebSocket) + React 18 + Vite (frontend) + PWA manifest + service worker  
**Access:** Via Tailscale HTTPS URL (e.g. `https://bort.[tailnet].ts.net`) — no public exposure  
**HTTPS:** Required for PWA install prompt. Enabled via `tailscale cert` on the RPi5 (free, auto-renewed Let's Encrypt cert for the `*.ts.net` domain)  
**Nginx:** Single reverse proxy — serves the static React/PWA build at `/`, proxies `/api` and `/ws` to FastAPI. Single origin, no CORS issues.  
**Design direction:** Dark control-room aesthetic, Syne + DM Sans + JetBrains Mono typography, electric blue + teal accent palette. No emoji icons; CSS animated status indicators.

### Install flow

1. Open `https://bort.[tailnet].ts.net` in Safari (iOS/Mac) or Chrome (Android/Mac)
2. Browser shows "Add to Home Screen" / "Install App" prompt
3. App installs as standalone (no browser chrome, own icon in dock/home screen)
4. Service worker caches the app shell for fast loads on subsequent opens

### Layout

- **Topbar:** Brand "Bort", real-time stats (queue / pending review / published today / errors)
- **Sidebar:** Bot list with live status dots, service health indicators, navigation (Pending / Published / Rejected / Settings / Logs)
- **Main area:** Video cards with thumbnail, Reddit source + upvote count, duration, age. Actions: Approve / Reject / Preview. Preview plays the video in-browser via streaming URL.

### Key flows

- **Approve:** video status → `approved`, pushed to `upload:pending` queue
- **Reject:** video status → `rejected`, moved to archive
- **Preview:** stream video file from API via signed temp URL
- **Bot management:** create/edit/pause bots from Settings view
- **Logs view:** tail Docker logs streamed via WebSocket
- **Offline:** service worker caches app shell; data requires Tailscale connection

---

## Upload Strategy

### Phase 1 — YouTube (launch)
- `google-api-python-client` with OAuth2 stored on RPi5
- YouTube Data API v3: free, 10,000 units/day (~6 uploads/day)
- Title, description, tags auto-generated from cleaned script + bot config
- Scheduled upload time configurable per bot

### Phase 2 — TikTok + Instagram (after YouTube validated)
- Playwright with persistent browser profile (cookies stored on NVMe)
- Manual login once; bot reuses session
- Headful Chromium with anti-detection flags
- Rate limit: 1–2 uploads/day per account initially
- Human-like delays: 500ms–2s randomised between actions

---

## Development & Deployment

### Dev (MacBook M4 Pro)
```bash
docker compose up --watch   # hot-reload on file changes
VIDEO_ENCODER=libx264
```

### Production (RPi5)
```bash
git pull && docker compose up -d
VIDEO_ENCODER=h264_v4l2m2m
# docker-compose.yml passes /dev/video0 to video-worker
```

Both machines are ARM64 — same images, no multi-arch needed.

### Deploy flow
1. Develop + test on MacBook
2. `git push` to repo (hosted on RPi5 itself via bare git repo, or GitHub)
3. SSH into RPi5 via Tailscale: `git pull && docker compose up -d`
4. Nginx serves the React build at `/` and proxies `/api` → FastAPI
5. HTTPS via `tailscale cert` — enables PWA install prompt on all devices

---

## Anti-Bot & Compliance

| Surface | Approach | Risk |
|---|---|---|
| Reddit scraping | PRAW with registered OAuth2 app | None — official API |
| YouTube upload | Official Data API v3 | None |
| TikTok upload | Playwright browser automation | Low-medium — mitigated by low frequency and session persistence |
| Instagram upload | Playwright browser automation | Low-medium — same mitigation |

---

## Phase Plan

| Phase | Scope | Goal |
|---|---|---|
| 1 | Scraper + TTS + Video Worker + Dashboard | Generate and review videos locally |
| 2 | YouTube upload integration | First real uploads, validate pipeline end-to-end |
| 3 | TikTok + Instagram upload | Multi-platform distribution |
| 4 | Second bot / second niche | Validate multi-bot architecture |
| 5 | Spanish language support | Duplicate content in ES for wider reach |

---

## Tech Stack Summary

| Layer | Technology |
|---|---|
| Language | Python 3.12 (all backend services) |
| TTS | Piper TTS (local, ARM64, free) |
| Video | FFmpeg (direct subprocess calls) |
| Queue | Redis 7 + `rq` (Redis Queue) |
| Database | SQLite (file on NVMe) |
| API | FastAPI + uvicorn |
| Frontend | React 18 + Vite + React Router + PWA (manifest.json + service worker) |
| Deployment | Docker Compose |
| Process mgmt | Docker (replaces systemd) |
| Upload (YT) | google-api-python-client |
| Upload (TT/IG) | Playwright |
| Scraping | PRAW |
