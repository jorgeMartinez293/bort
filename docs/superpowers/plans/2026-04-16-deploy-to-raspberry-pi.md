# Raspberry Pi Deployment Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy bort to Raspberry Pi 5 for 24/7 production operation and establish a git-based update workflow from MacBook → RPi with zero database loss.

**Architecture:** GitHub is the single source of truth for code. Media files (backgrounds, TTS models, music) and credentials (`.env`) live only on each machine — never in git. Updates flow via `git pull` + selective `docker compose` restart on the RPi. The SQLite DB and all generated media are in Docker bind-mount volumes (`./data/`, `./media/generated/`) so they survive every deployment.

**Tech Stack:** Docker Compose, SSH, rsync, git, GitHub

---

## Key facts before you start

| Thing | Mac (dev) | RPi (prod) |
|---|---|---|
| Video encoder | `libx264` | `h264_v4l2m2m` |
| Piper binary | aarch64 (same Dockerfile) | aarch64 |
| `ui` dev server | runs | NOT started |
| nginx | proxies to dev server port | serves built static bundle |
| DB path | `./data/db/bort.db` | `~/bort/data/db/bort.db` |

nginx **does not proxy to the `ui` service** — it always serves the pre-built static bundle baked into the nginx Docker image (`/usr/share/nginx/html`). The `ui` service is only needed on Mac for hot-reload during development.

---

## Task 1: Push code to GitHub

**Files:**
- No code changes. Just git commands.

- [ ] **Create repo on GitHub** (github.com/new → name `bort`, private)

- [ ] **Add remote and push**
```bash
cd ~/Desktop/proyectos/bort
git remote add origin git@github.com:<tu-usuario>/bort.git
git push -u origin main
```

- [ ] **Verify `.gitignore` excludes secrets and large files**
```bash
git status --short
# Should NOT see: .env, data/, media/, __pycache__
```
The existing `.gitignore` already excludes `.env`, `/data/`, `/media/`, `*.db`. ✓

---

## Task 2: Create `docker-compose.prod.yml` (production override)

**Files:**
- Create: `docker-compose.prod.yml`

The only production difference is that the `ui` dev server should not start — nginx serves static files from its own built bundle.

- [ ] **Create the file**
```yaml
# docker-compose.prod.yml — Raspberry Pi production overrides
# Usage: docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
services:
  ui:
    profiles:
      - dev          # only starts when: docker compose --profile dev up

  nginx:
    depends_on:
      - api          # no longer depends on ui
```

- [ ] **Verify it works locally (optional sanity check)**
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --services
# Expected output (no 'ui'):
# redis
# scraper
# tts-worker
# video-worker
# upload-worker
# scheduler
# api
# nginx
```

- [ ] **Commit**
```bash
git add docker-compose.prod.yml
git commit -m "deploy: add production compose override (no ui dev server)"
git push
```

---

## Task 3: Create deploy script

**Files:**
- Create: `scripts/deploy.sh`

- [ ] **Create the script**
```bash
#!/usr/bin/env bash
# scripts/deploy.sh — push latest code from Mac to Raspberry Pi
#
# Usage:
#   ./scripts/deploy.sh                    # uses default RPI_HOST
#   RPI_HOST=pi@192.168.1.50 ./scripts/deploy.sh
#
# What it does:
#   1. git pull on the RPi
#   2. Rebuild only images whose build context changed (Docker layer cache handles the rest)
#   3. Restart services — DB and generated media are untouched (bind-mount volumes)

set -euo pipefail

RPI_HOST="${RPI_HOST:-bort@raspberrypi.local}"
RPI_DIR="${RPI_DIR:-~/bort}"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

echo "▸ Deploying to ${RPI_HOST}:${RPI_DIR}"

ssh "$RPI_HOST" "
  set -euo pipefail
  cd ${RPI_DIR}

  echo '▸ Pulling latest code…'
  git pull

  echo '▸ Rebuilding and restarting services…'
  ${COMPOSE} up --build -d

  echo '▸ Status:'
  ${COMPOSE} ps --format 'table {{.Name}}\t{{.Status}}'
"

echo "✓ Deploy complete"
```

- [ ] **Make it executable and commit**
```bash
chmod +x scripts/deploy.sh
git add scripts/deploy.sh
git commit -m "deploy: add RPi deploy script"
git push
```

---

## Task 4: Prepare Raspberry Pi (one-time)

Run these commands **on the RPi** (via SSH or directly with keyboard+monitor).

- [ ] **Install Docker**
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker          # apply group without logout
docker run --rm hello-world   # verify
```

- [ ] **Install git and rsync**
```bash
sudo apt-get update && sudo apt-get install -y git rsync
```

- [ ] **Add your Mac's SSH public key to the RPi** (run on Mac)
```bash
ssh-copy-id bort@raspberrypi.local
# Or: ssh-copy-id bort@<ip-address>
```

- [ ] **Verify passwordless SSH from Mac**
```bash
ssh bort@raspberrypi.local echo "ok"
# Expected: ok
```

- [ ] **Clone the repo on the RPi**
```bash
# On RPi:
git clone git@github.com:<tu-usuario>/bort.git ~/bort
# If SSH key not set up on RPi yet, use HTTPS:
# git clone https://github.com/<tu-usuario>/bort.git ~/bort
```

---

## Task 5: Transfer media files (one-time, run on Mac)

These files are in `.gitignore` — they must be copied manually. Only needed once (or when you add new backgrounds/models).

- [ ] **Transfer TTS models (~121 MB)**
```bash
rsync -avz --progress \
  ~/Desktop/proyectos/bort/media/tts_models/ \
  bort@raspberrypi.local:~/bort/media/tts_models/
```

- [ ] **Transfer background clips (~1.2 GB — takes a few minutes)**
```bash
rsync -avz --progress \
  ~/Desktop/proyectos/bort/media/backgrounds/ \
  bort@raspberrypi.local:~/bort/media/backgrounds/
```

- [ ] **Transfer music (~7 MB)**
```bash
rsync -avz --progress \
  ~/Desktop/proyectos/bort/media/music/ \
  bort@raspberrypi.local:~/bort/media/music/
```

- [ ] **Verify on RPi**
```bash
ssh bort@raspberrypi.local "du -sh ~/bort/media/*"
# Expected: ~1.2G backgrounds, ~6.8M music, ~121M tts_models
```

---

## Task 6: Configure `.env` on the RPi (one-time)

- [ ] **Create `.env` on the RPi** — copy from Mac and change the encoder
```bash
scp ~/Desktop/proyectos/bort/.env bort@raspberrypi.local:~/bort/.env
ssh bort@raspberrypi.local "
  sed -i 's/VIDEO_ENCODER=libx264/VIDEO_ENCODER=h264_v4l2m2m/' ~/bort/.env
  grep VIDEO_ENCODER ~/bort/.env   # verify: VIDEO_ENCODER=h264_v4l2m2m
"
```

---

## Task 7: First build and start on RPi

Building images the first time on RPi5 takes ~15 minutes. Subsequent builds use Docker layer cache and are much faster.

- [ ] **Build and start all services (run on RPi or via deploy script)**
```bash
# On RPi:
cd ~/bort
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

- [ ] **Watch logs to confirm all services start cleanly**
```bash
docker compose logs -f --tail=20
# Expected: scraper logs "Scraped N new posts", tts-worker starts, etc.
# Give it ~2 minutes for the first scrape to run
```

- [ ] **Verify dashboard is accessible**

Open `http://raspberrypi.local` (or `http://<rpi-ip>`) in the browser on any device on the same network.

- [ ] **Check DB after first scrape**
```bash
sqlite3 ~/bort/data/db/bort.db "SELECT COUNT(*) FROM content;"
# Expected: > 0 after scraper runs
```

---

## Task 8: Auto-start on boot (one-time, on RPi)

- [ ] **Create systemd service**
```bash
sudo tee /etc/systemd/system/bort.service << 'EOF'
[Unit]
Description=Bort video pipeline
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/bort/bort
ExecStart=/usr/bin/docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.yml -f docker-compose.prod.yml down
User=bort
Group=docker
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable bort
sudo systemctl start bort
```

- [ ] **Verify it starts on boot**
```bash
sudo reboot
# After reboot:
ssh bort@raspberrypi.local "docker compose -C ~/bort ps"
```

---

## Update workflow (ongoing)

Once everything is deployed, this is the daily update flow:

### Code change (Python services or frontend)
```bash
# On Mac — after git commit + push:
./scripts/deploy.sh
```
This SSHes in, `git pull`s, and runs `docker compose up --build -d`. Docker layer cache means only services with changed build context get rebuilt. The DB and all generated media survive untouched.

### Adding new background clips or music
```bash
rsync -avz --progress \
  ~/Desktop/proyectos/bort/media/backgrounds/ \
  bort@raspberrypi.local:~/bort/media/backgrounds/
```
No restart needed — the video worker reads from disk at render time.

### Emergency restart (without code update)
```bash
ssh bort@raspberrypi.local "cd ~/bort && docker compose -f docker-compose.yml -f docker-compose.prod.yml restart"
```

### Check logs from Mac
```bash
ssh bort@raspberrypi.local "cd ~/bort && docker compose logs --tail=50 video-worker"
```

---

## What is NEVER lost during updates

| Data | Location | Safe? |
|---|---|---|
| SQLite DB | `~/bort/data/db/bort.db` | ✓ bind-mount, never touched by compose |
| Generated videos | `~/bort/media/generated/videos/` | ✓ bind-mount |
| Generated audio | `~/bort/media/generated/audio/` | ✓ bind-mount |
| Bot configuration | inside SQLite | ✓ |
| Queue state (Redis) | `~/bort/data/redis/` | ✓ bind-mount |

`docker compose up --build -d` only rebuilds images and restarts containers — it never touches bind-mounted host directories.
