#!/bin/bash
set -e

# Ensure data directories exist
mkdir -p /app/data/screenshots
mkdir -p /app/data/text
mkdir -p /app/data/html
mkdir -p /app/data/browser_profile/ctrip
mkdir -p /app/data/debug

# Create default settings.json for headless mode if not exists
if [ ! -f /app/data/settings.json ]; then
    echo '{"headless": true}' > /app/data/settings.json
    echo "[entrypoint] Created default settings.json with headless=true"
fi

echo "[entrypoint] Starting FlightClaw backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
