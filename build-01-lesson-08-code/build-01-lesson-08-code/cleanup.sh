#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "==> Cleaning repository-local artifacts"

# Remove local Python/test artifacts that are not useful for git push.
rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov build dist
rm -f .coverage coverage.xml

shopt -s nullglob globstar
for d in **/__pycache__; do
  rm -rf "$d"
done
for f in **/*.pyc **/*.pyo; do
  rm -f "$f"
done

echo "==> Checking for potential hardcoded secrets"
if rg -n -i \
  "(OPENAI|ANTHROPIC|GITHUB|FIREBASE|DATABASE)_?(API)?_?(KEY|TOKEN|SECRET|PASSWORD)\\s*[:=]|AKIA[0-9A-Z]{16}|-----BEGIN (RSA|EC|OPENSSH|DSA) PRIVATE KEY-----" \
  --glob "!.venv/**" \
  --glob "!.git/**" \
  --glob "!cleanup.sh" \
  --glob "*.{env,ini,yaml,yml,json,py,sh,md,toml}" .; then
  echo "Potential secret-like values found above. Review before git push."
else
  echo "No API key/secret patterns detected in project files."
fi

echo "==> Stopping Docker Compose services (if any)"
if [ -f docker-compose.yml ] || [ -f compose.yml ] || [ -f compose.yaml ]; then
  docker compose down --remove-orphans || true
fi

echo "==> Pruning unused Docker resources"
docker container prune -f || true
docker image prune -af || true
docker network prune -f || true
docker volume prune -f || true
docker builder prune -af || true

echo "==> Done. Current git status:"
git status --short || true
