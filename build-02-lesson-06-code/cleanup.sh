#!/usr/bin/env bash
# Cortex — Build 02, Lesson 06 — local + Docker cleanup before git push
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT}"

echo "Cortex — Build 02, Lesson 06 cleanup"
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

echo "Local cleanup..."

# Virtualenv, caches, and runtime artifacts — not for git
for path in .venv __pycache__ .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage model.pt; do
  remove_path_if_exists "${path}"
done

find . -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true

# Env / secret files (API keys, tokens) — never keep these in the tree
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
    model.pt \
    .env .env.local .env.production .env.development \
    secrets.json credentials.json \
    >/dev/null 2>&1 || true
fi

echo "Local cleanup complete."
echo ""

echo "Docker cleanup..."

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or not on PATH — skipping Docker cleanup."
  echo ""
  echo "Cleanup finished (local only)."
  exit 0
fi

if ! timeout 10 docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running or did not respond — skipping Docker cleanup."
  echo ""
  echo "Cleanup finished (local only)."
  exit 0
fi

echo "Stopping all running containers..."
running="$(docker ps -q || true)"
if [[ -n "${running}" ]]; then
  # shellcheck disable=SC2086
  docker stop ${running}
else
  echo "  No running containers."
fi

echo "Removing stopped containers, unused networks, dangling images, volumes, and build cache..."
docker system prune -af --volumes

echo "Removing unused images..."
docker image prune -af

echo ""
echo "Docker disk usage:"
docker system df

echo ""
echo "Cleanup finished. Safe to git push after:"
echo "  git add ."
echo "  git status    # verify .venv/, caches, model.pt, and .env files are not listed"
echo ""
echo "To run again later:"
echo "  ./setup.sh"
echo "  python lesson_code.py"
