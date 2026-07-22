#!/usr/bin/env bash
# Cortex — doctor.sh
# Checks the local dev machine, not the repo (that was Lesson 01) and not
# the running service (that's Build 09's observability). Same instinct,
# different layer: fail fast, and say exactly what's wrong.

set -euo pipefail

status=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then
    echo "[PASS] $name"
  else
    echo "[FAIL] $name"
    status=1
  fi
}

warn_only() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then
    echo "[PASS] $name"
  else
    echo "[WARN] $name (not required until Build 01, Lesson 07)"
  fi
}

echo "Cortex dev environment check"
echo "----------------------------------------"
check     "python3 >= 3.11"  "python3 -c 'import sys; assert sys.version_info >= (3, 11)'"
check     "git installed"    "command -v git"
warn_only "docker installed" "command -v docker"
echo "----------------------------------------"

if [[ "$status" -eq 0 ]]; then
  echo "All required checks passed."
else
  echo "Some required checks failed — see above."
fi

exit "$status"
