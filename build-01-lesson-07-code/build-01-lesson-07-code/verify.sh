#!/usr/bin/env bash
# Quick smoke test — tries Docker API (8888) then local uvicorn (8000).
set -euo pipefail

cd "$(dirname "$0")"

check() {
  local port=$1
  local label=$2
  if curl -sf "http://localhost:${port}/health" >/dev/null 2>&1; then
    echo "OK  ${label} (port ${port})"
    curl -s "http://localhost:${port}/health"
    echo ""
    return 0
  fi
  echo "FAIL ${label} (port ${port}) — not reachable"
  return 1
}

echo "Checking Cortex endpoints..."
ok=0
check 8888 "Docker Compose API" && ok=1 || true
check 8000 "local uvicorn API" && ok=1 || true

if [[ $ok -eq 0 ]]; then
  echo ""
  echo "Nothing is running. Start one of:"
  echo "  ./start.sh    # full Docker stack on port 8888"
  echo "  ./dev.sh      # Postgres in Docker + uvicorn on port 8000"
  exit 1
fi
