#!/usr/bin/env bash
# scripts/deploy.sh — push latest code from Mac to Raspberry Pi
#
# Usage:
#   ./scripts/deploy.sh
#   RPI_HOST=bort@other-ip ./scripts/deploy.sh

set -euo pipefail

RPI_HOST="${RPI_HOST:-jorge@100.91.82.40}"
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
