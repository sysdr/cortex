#!/usr/bin/env bash
# Run the lesson test suite with the project virtualenv (not system Python).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "No .venv found. Run ./setup.sh first." >&2
  exit 1
fi

exec .venv/bin/pytest test_lesson.py "$@"
