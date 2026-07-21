#!/usr/bin/env bash
# Stop Cortex containers and remove local/generated files before git push.
set -euo pipefail

cd "$(dirname "$0")"

echo "=== Cortex cleanup ==="

# Stop any local uvicorn dev server on port 8000
if command -v lsof >/dev/null 2>&1; then
  pids=$(lsof -ti :8000 2>/dev/null || true)
  if [[ -n "${pids:-}" ]]; then
    echo "Stopping local process(es) on port 8000: $pids"
    kill $pids 2>/dev/null || true
  fi
elif command -v fuser >/dev/null 2>&1; then
  fuser -k 8000/tcp 2>/dev/null || true
fi

# Stop project containers, networks, and volumes
if command -v docker >/dev/null 2>&1; then
  echo "Stopping Docker Compose stack..."
  docker compose down -v --remove-orphans 2>/dev/null || true

  echo "Removing project Docker image (if present)..."
  docker image rm build-01-lesson-07-code-api:latest 2>/dev/null || true

  echo "Pruning unused Docker resources..."
  docker container prune -f 2>/dev/null || true
  docker network prune -f 2>/dev/null || true
  docker volume prune -f 2>/dev/null || true
  docker image prune -f 2>/dev/null || true
else
  echo "Docker not available — skipping container cleanup."
fi

# Remove local Python environment and caches
echo "Removing local Python artifacts..."
rm -rf .venv __pycache__ .pytest_cache
find . -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find . -type f -name '*.pyc' -delete 2>/dev/null || true

# Remove env/secret files (never commit these)
echo "Removing env/secret files..."
find . -maxdepth 1 -type f \( -name '.env' -o -name '.env.*' \) ! -name '.env.example' -delete 2>/dev/null || true

# Remove generated seed JSON (recreate with ./seed.sh)
echo "Removing generated seed data..."
rm -f data/documents/*.json

echo ""
echo "Cleanup complete. Safe to git push after:"
echo "  git add ."
echo "  git status    # verify .venv/, caches, and seed JSON are not listed"
echo ""
echo "To run again later:"
echo "  ./setup.sh && ./start.sh"
