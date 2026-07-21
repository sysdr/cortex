#!/usr/bin/env bash
# Cortex — Build 01, Lesson 06 — environment setup
set -euo pipefail

echo "Setting up Lesson 06 environment..."

python3 --version | grep -qE "3\.(1[1-9]|[2-9][0-9])" || {
  echo "Python 3.11+ required. Found: $(python3 --version)"
  exit 1
}

python3 -m venv .venv
. .venv/bin/activate

pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "Done. Python environment ready."
echo ""
echo "Same Postgres as Lesson 05:"
echo "  postgresql://postgres:postgres@127.0.0.1:5432/cortex"
echo "(override with CORTEX_DATABASE_URL if yours differs)"
echo ""
echo "This lesson's schema.sql is safe to run against Lesson 05's existing"
echo "tables — it ALTERs them forward instead of assuming a clean database."
echo ""
echo "  Run the demo:  python lesson_code.py"
echo "  Run the tests: pytest test_lesson.py -v"
