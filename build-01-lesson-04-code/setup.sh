#!/usr/bin/env bash
# Cortex — Build 01, Lesson 04 — environment setup
set -euo pipefail

echo "Setting up Lesson 04 environment..."

python3 --version | grep -qE "3\.(1[1-9]|[2-9][0-9])" || {
  echo "Python 3.11+ required. Found: $(python3 --version)"
  exit 1
}

chmod +x seed.sh

python3 -m venv .venv
. .venv/bin/activate

pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "Done. Environment ready."
echo "  Seed sample data:      ./seed.sh ./data/documents"
echo "  Run the API:           uvicorn lesson_code:app --reload"
echo "  Run the tests:         pytest test_lesson.py -v"
