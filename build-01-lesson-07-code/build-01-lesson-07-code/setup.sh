#!/usr/bin/env bash
# Cortex — Build 01, Lesson 07 — environment setup
set -euo pipefail

echo "Setting up Lesson 07 environment..."

python3 --version | grep -qE "3\.(1[1-9]|[2-9][0-9])" || {
  echo "Python 3.11+ required. Found: $(python3 --version)"
  exit 1
}

chmod +x seed.sh start.sh dev.sh verify.sh cleanup.sh

python3 -m venv .venv
. .venv/bin/activate

pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "Done. Python environment ready (for running tests without Docker)."
echo ""
echo "=== Path A: Docker Compose (what this lesson is actually about) ==="
echo "  ./seed.sh ./data/documents"
echo "  ./start.sh"
echo "  # or: docker compose up --build -d"
echo "  # in another terminal:"
echo "  curl http://localhost:8888/documents?owner_id=user-1"
echo "  docker compose down          # stop"
echo "  docker compose down -v       # stop and wipe the Postgres volume"
echo ""
echo "=== Path B: local uvicorn + Postgres in Docker (WSL-friendly) ==="
echo "  ./dev.sh"
echo "  # in another terminal:"
echo "  curl http://localhost:8000/health"
echo "  source .venv/bin/activate && pytest test_lesson.py -v"
