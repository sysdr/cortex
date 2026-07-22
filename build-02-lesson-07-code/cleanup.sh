#!/usr/bin/env bash
# Cortex — Build 02, Lesson 07 — local + Docker cleanup before git push
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT}"

echo "Cortex — Build 02 Milestone cleanup"
echo "Working directory: ${ROOT}"
echo ""

remove_path_if_exists() {
  local target="$1"
  if [[ -e "${target}" ]]; then
    rm -rf "${target}"
    echo "  Removed: ${target}"
  else
    echo "  Not found (skip): ${target}"
  fi
}

echo "Stopping local API server (port 8000)..."
if command -v fuser >/dev/null 2>&1; then
  fuser -k 8000/tcp 2>/dev/null || true
elif command -v lsof >/dev/null 2>&1; then
  pids="$(lsof -ti :8000 2>/dev/null || true)"
  if [[ -n "${pids}" ]]; then
    # shellcheck disable=SC2086
    kill ${pids} 2>/dev/null || true
  fi
fi
pkill -f 'uvicorn lesson_code:app' 2>/dev/null || true

echo ""
echo "Local cleanup..."

for path in .venv __pycache__ .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage; do
  remove_path_if_exists "${path}"
done

find . -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true

for path in .env .env.local .env.production .env.development secrets.json credentials.json; do
  remove_path_if_exists "${path}"
done

shopt -s nullglob
for path in .env.*; do
  [[ "${path}" == ".env.example" ]] && continue
  remove_path_if_exists "${path}"
done
shopt -u nullglob

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Untracking ignored paths from git index (if present)..."
  git rm -r --cached --ignore-unmatch \
    .venv __pycache__ .pytest_cache .mypy_cache .ruff_cache htmlcov \
    .env .env.local .env.production .env.development \
    secrets.json credentials.json \
    >/dev/null 2>&1 || true
fi

echo ""
echo "Docker cleanup..."

docker_cmd() {
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    docker "$@"
    return 0
  fi

  local docker_exe="/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe"
  if [[ -x "${docker_exe}" ]] && "${docker_exe}" info >/dev/null 2>&1; then
    "${docker_exe}" "$@"
    return 0
  fi

  return 1
}

if ! docker_cmd info >/dev/null 2>&1; then
  echo "Docker is not available or the daemon is not running — skipping Docker cleanup."
  echo ""
  echo "Cleanup finished (local only)."
  exit 0
fi

echo "Stopping lesson Postgres container (cortex-postgres)..."
docker_cmd rm -f cortex-postgres 2>/dev/null || true

echo "Stopping all running containers..."
running="$(docker_cmd ps -q 2>/dev/null || true)"
if [[ -n "${running}" ]]; then
  # shellcheck disable=SC2086
  docker_cmd stop ${running} 2>/dev/null || true
else
  echo "  No running containers."
fi

echo "Removing stopped containers, unused networks, dangling images, volumes, and build cache..."
docker_cmd system prune -af --volumes 2>/dev/null || true

echo "Removing unused images..."
docker_cmd image prune -af 2>/dev/null || true

echo ""
echo "Docker disk usage:"
docker_cmd system df 2>/dev/null || true

echo ""
echo "Cleanup finished. Safe to git push after:"
echo "  git add ."
echo "  git status    # verify .venv/, caches, and .env files are not listed"
echo ""
echo "To run again later:"
echo "  ./setup.sh"
echo "  docker run -d --name cortex-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=cortex -p 5432:5432 postgres:16-alpine"
