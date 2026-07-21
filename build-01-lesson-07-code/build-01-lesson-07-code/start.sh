#!/usr/bin/env bash
# Start Cortex via Docker Compose (background) and wait until healthy.
set -euo pipefail

cd "$(dirname "$0")"

./seed.sh ./data/documents

echo "Starting Docker Compose..."
docker compose up --build -d

echo "Waiting for API..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8888/health >/dev/null 2>&1; then
    echo ""
    echo "Cortex is up."
    echo "  curl http://localhost:8888/health"
    echo "  curl \"http://localhost:8888/documents?owner_id=user-1\""
    echo ""
    echo "Stop with: docker compose down"
    exit 0
  fi
  sleep 1
done

echo "API did not become ready in time. Check logs:"
echo "  docker compose logs"
exit 1
