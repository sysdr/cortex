#!/usr/bin/env bash
# Cortex — Build 02, Lesson 04 — environment setup
set -euo pipefail

echo "Setting up Build 02, Lesson 04 environment..."

python3 --version | grep -qE "3\.(1[1-9]|[2-9][0-9])" || {
  echo "Python 3.11+ required. Found: $(python3 --version)"
  exit 1
}

python3 -m venv .venv
. .venv/bin/activate

pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "Done. Environment ready. No database needed for this lesson."
echo "  Run the demo:  python lesson_code.py"
echo "  Run the tests: pytest test_lesson.py -v"
