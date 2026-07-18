#!/usr/bin/env bash
# Cortex — stop containers and reclaim unused Docker resources
set -euo pipefail

echo "Docker cleanup starting..."

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or not on PATH — nothing to clean."
  exit 0
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running — start Docker and re-run this script."
  exit 1
fi

echo "Stopping all running containers..."
running="$(docker ps -q || true)"
if [[ -n "${running}" ]]; then
  docker stop ${running}
else
  echo "  No running containers."
fi

echo "Removing stopped containers, unused networks, dangling images, and build cache..."
docker system prune -af --volumes

echo "Removing unused images..."
docker image prune -af

echo ""
echo "Docker cleanup complete."
docker system df
