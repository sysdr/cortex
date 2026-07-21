#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "Starting repository cleanup in: $ROOT_DIR"

remove_path_if_exists() {
  local target="$1"
  if [ -e "$target" ]; then
    if rm -rf "$target" 2>/dev/null; then
      echo "Removed: $target"
    else
      echo "Could not remove (permission issue): $target"
    fi
  else
    echo "Not found (skip): $target"
  fi
}

# Remove common local-only Python artifacts that should not be pushed.
remove_path_if_exists ".venv"
remove_path_if_exists ".pytest_cache"
remove_path_if_exists "__pycache__"

# Remove recursive Python cache files/folders.
python3 - <<'PY'
from pathlib import Path
import shutil

root = Path(".").resolve()
removed_dirs = 0
removed_files = 0

for path in root.rglob("__pycache__"):
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
        removed_dirs += 1

for pattern in ("*.pyc", "*.pyo", "*.pyd"):
    for file_path in root.rglob(pattern):
        if file_path.is_file():
            file_path.unlink(missing_ok=True)
            removed_files += 1

print(f"Removed recursive caches: {removed_dirs} dirs, {removed_files} files")
PY

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed. Skipping Docker cleanup."
  exit 0
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not available. Skipping Docker cleanup."
  exit 0
fi

echo "Stopping running Docker containers (if any)..."
running_containers="$(docker ps -q)"
if [ -n "$running_containers" ]; then
  # shellcheck disable=SC2086
  docker stop $running_containers || true
else
  echo "No running containers found."
fi

echo "Pruning stopped containers..."
docker container prune -f || true

echo "Pruning unused images..."
docker image prune -af || true

echo "Pruning unused networks..."
docker network prune -f || true

echo "Pruning unused volumes..."
docker volume prune -f || true

echo "Running full Docker system prune..."
docker system prune -af --volumes || true

echo "Cleanup complete."
