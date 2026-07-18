#!/usr/bin/env bash
# Cortex — Build 01, Lesson 03 — local + Docker cleanup
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT}"

# Lesson sources live in a nested directory in this repo
LESSON_DIR="${ROOT}/build-01-lesson-03-code"
if [[ ! -d "${LESSON_DIR}" ]]; then
  LESSON_DIR="${ROOT}"
fi

echo "Local cleanup starting..."

clean_local_artifacts() {
  local dir="$1"
  [[ -d "${dir}" ]] || return 0
  (
    cd "${dir}"
    for path in .venv __pycache__ .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage data; do
      if [[ -e "${path}" ]]; then
        echo "  Removing ${dir}/${path}"
        rm -rf "${path}"
      fi
    done

    find . -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
    find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true

    # Env / secret files (API keys, tokens) — never keep these in the tree
    for path in .env .env.local .env.production .env.development secrets.json credentials.json; do
      if [[ -e "${path}" ]]; then
        echo "  Removing secret file ${dir}/${path}"
        rm -f "${path}"
      fi
    done
    shopt -s nullglob
    for path in .env.*; do
      echo "  Removing secret file ${dir}/${path}"
      rm -f "${path}"
    done
    shopt -u nullglob
  )
}

clean_local_artifacts "${ROOT}"
if [[ "${LESSON_DIR}" != "${ROOT}" ]]; then
  clean_local_artifacts "${LESSON_DIR}"
fi

# Untrack ignored paths if they were committed earlier
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Untracking ignored paths from git index (if present)..."
  git rm -r --cached --ignore-unmatch \
    build-01-lesson-03-code/.venv \
    build-01-lesson-03-code/__pycache__ \
    build-01-lesson-03-code/.pytest_cache \
    build-01-lesson-03-code/.mypy_cache \
    build-01-lesson-03-code/.ruff_cache \
    build-01-lesson-03-code/htmlcov \
    build-01-lesson-03-code/data \
    build-01-lesson-03-code/.env \
    build-01-lesson-03-code/.env.local \
    build-01-lesson-03-code/.env.production \
    build-01-lesson-03-code/.env.development \
    build-01-lesson-03-code/secrets.json \
    build-01-lesson-03-code/credentials.json \
    .venv __pycache__ .pytest_cache .mypy_cache .ruff_cache htmlcov data \
    .env .env.local .env.production .env.development \
    secrets.json credentials.json \
    >/dev/null 2>&1 || true
fi

echo "Local cleanup complete."
echo ""

echo "Docker cleanup starting..."

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or not on PATH — skipping Docker cleanup."
  exit 0
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running — start Docker and re-run this script for Docker cleanup."
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
echo "Docker cleanup complete."
docker system df

echo ""
echo "Cleanup finished."
