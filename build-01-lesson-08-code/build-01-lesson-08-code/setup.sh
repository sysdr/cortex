#!/usr/bin/env bash
# Cortex — Build 01, Lesson 08 (Build Milestone) — environment setup
set -euo pipefail

echo "Cortex — Build 01 Milestone setup"
echo ""

chmod +x seed.sh doctor.sh

echo "--- Step 1: dev environment check (Lesson 03) ---"
./doctor.sh || {
  echo "Fix the failed checks above before continuing."
  exit 1
}

echo ""
echo "--- Step 2: python environment (for tests / non-Docker path) ---"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "Done."

API_PORT="${CORTEX_HOST_PORT:-8000}"
if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a
  . ./.env
  set +a
  API_PORT="${CORTEX_HOST_PORT:-8000}"
fi

echo ""
echo "=== This is the milestone — the real path is Docker Compose ==="
echo "  ./seed.sh ./data/documents"
echo "  docker compose up --build"
echo ""
echo "Then, in another terminal, hit every endpoint built since Lesson 04:"
echo "  curl http://localhost:${API_PORT}/health"
echo "  curl http://localhost:${API_PORT}/documents?owner_id=user-1"
echo "  curl -X POST http://localhost:${API_PORT}/documents -H 'Content-Type: application/json' \\"
echo "       -d '{\"title\":\"My Doc\",\"body\":\"hello\",\"owner_id\":\"me\",\"tags\":[\"first\"]}'"
echo ""
echo "=== Or, to run the full smoke test suite without Docker ==="
echo "  (needs local Postgres — see Lesson 05's setup.sh)"
echo "  .venv/bin/pytest test_lesson.py -v"
