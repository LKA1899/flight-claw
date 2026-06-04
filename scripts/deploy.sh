#!/bin/bash
# flight-scan deploy/update script.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

APP_PORT="${APP_PORT:-8081}"
NO_CACHE="${NO_CACHE:-0}"

echo "================================================"
echo " flight-scan deploy"
echo "================================================"
echo "Project: $PROJECT_DIR"
echo "Port:    $APP_PORT"
echo "NoCache: $NO_CACHE"

if [ ! -f .env.production ]; then
    echo "[ERROR] .env.production is missing."
    echo "Copy .env.production.example to .env.production and edit it before deploying."
    exit 1
fi

mkdir -p data/screenshots data/text data/html data/browser_profile/ctrip data/debug

if [ ! -f data/settings.json ]; then
    echo '{"headless": true}' > data/settings.json
    echo "[INFO] Created data/settings.json with headless=true"
fi

echo "[1/3] Stop old containers..."
docker compose down --remove-orphans

echo "[2/3] Build images from local cache..."
if [ "$NO_CACHE" = "1" ]; then
    APP_PORT="$APP_PORT" docker compose build --no-cache
else
    APP_PORT="$APP_PORT" docker compose build
fi

echo "[3/3] Start services..."
APP_PORT="$APP_PORT" docker compose up -d

echo "[INFO] Waiting for service..."
sleep 5

if curl -sf "http://localhost:${APP_PORT}/api/overview" > /dev/null 2>&1; then
    echo "================================================"
    echo " Deploy succeeded"
    echo "================================================"
    echo "URL: http://<SERVER_IP>:${APP_PORT}"
    echo "Logs: docker compose logs -f"
else
    echo "[WARN] Service did not pass health check yet."
    echo "Check logs:"
    echo "  docker compose logs -f backend"
    echo "  docker compose logs -f nginx"
    exit 2
fi
