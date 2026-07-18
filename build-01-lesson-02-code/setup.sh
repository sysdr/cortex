#!/usr/bin/env bash
# Cortex — Build 01, Lesson 02 — environment setup
set -euo pipefail

echo "Setting up Lesson 02 environment..."

python3 --version | grep -qE "3\.(1[1-9]|[2-9][0-9])" || {
  echo "Python 3.11+ required. Found: $(python3 --version)"
  exit 1
}

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "Done. Environment ready."
echo "  Run the demo:  source .venv/bin/activate && python lesson_code.py"
echo "  Run the tests:  source .venv/bin/activate && pytest test_lesson.py -v"
