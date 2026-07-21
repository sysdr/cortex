#!/usr/bin/env bash
# Path B: Postgres in Docker, API via local uvicorn on port 8000.
# Use this on WSL when Docker cannot publish host port 8000.
set -euo pipefail

cd "$(dirname "$0")"

./seed.sh ./data/documents

echo "Starting Postgres..."
docker compose up postgres -d

echo "Waiting for Postgres..."
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
  echo "Postgres did not become ready. Check: docker compose logs postgres"
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "Run ./setup.sh first to create the Python environment."
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo ""
echo "Starting uvicorn on http://127.0.0.1:8000"
echo "  curl http://localhost:8000/health"
echo "  curl \"http://localhost:8000/documents?owner_id=user-1\""
echo ""
exec uvicorn lesson_code:app --host 127.0.0.1 --port 8000 --reload
