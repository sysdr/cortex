#!/usr/bin/env bash
# Cortex — Build 01, Lesson 06 — pre-push cleanup
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LESSON_CONTAINER="${CORTEX_POSTGRES_CONTAINER:-cortex-postgres}"

docker_cmd() {
  if command -v docker >/dev/null 2>&1; then
    if docker version >/dev/null 2>&1; then
      docker "$@"
      return
    fi
  fi

  local win_docker="/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe"
  if [[ -f "$win_docker" ]]; then
    "$win_docker" "$@"
    return
  fi

  return 1
}

echo "=== Removing local artifacts (not for git) ==="

rm -rf .venv .pytest_cache __pycache__
find . -type d -name '__pycache__' -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
find . -type f -name '*.py[cod]' -not -path './.venv/*' -delete 2>/dev/null || true

for secret_file in .env .env.local .env.development .env.production; do
  if [[ -f "$secret_file" ]]; then
    echo "Removing $secret_file (may contain secrets)"
    rm -f "$secret_file"
  fi
done

echo "=== Docker cleanup ==="

if docker_cmd version >/dev/null 2>&1; then
  if docker_cmd ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$LESSON_CONTAINER"; then
    echo "Stopping and removing $LESSON_CONTAINER..."
    docker_cmd stop "$LESSON_CONTAINER" >/dev/null 2>&1 || true
    docker_cmd rm "$LESSON_CONTAINER" >/dev/null 2>&1 || true
  fi

  echo "Removing stopped containers..."
  docker_cmd container prune -f

  echo "Removing unused images..."
  docker_cmd image prune -f

  echo "Removing unused networks, build cache, and dangling resources..."
  docker_cmd system prune -f
else
  echo "Docker not available — skipped container cleanup."
fi

echo ""
echo "Done. Safe to git push:"
echo "  README.md  lesson_code.py  schema.sql  setup.sh  test_lesson.py"
echo "  requirements.txt  pytest.ini  cleanup.sh  .gitignore"
echo ""
echo "Re-run ./setup.sh before working on the lesson again."
