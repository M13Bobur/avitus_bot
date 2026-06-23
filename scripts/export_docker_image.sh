#!/bin/sh
# Build image locally and export for slow-server deploy (no pip download on server).
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

IMAGE_NAME="${IMAGE_NAME:-pharm_bot-bot}"
OUTPUT="${OUTPUT:-pharm_bot_image.tar.gz}"

echo "Building $IMAGE_NAME..."
docker compose build bot

echo "Saving to $OUTPUT..."
docker save "$IMAGE_NAME:latest" | gzip > "$OUTPUT"

echo "Done. Copy to server:"
echo "  scp $OUTPUT user@server:~/"
echo "On server:"
echo "  docker load < pharm_bot_image.tar.gz"
echo "  cd ~/pharm_bot && docker compose up -d bot"
