#!/usr/bin/env bash
# Cortex — Build 01, Lesson 01 — environment setup
set -euo pipefail

echo "Setting up Lesson 01 environment..."

python3 --version | grep -qE "3\.(1[1-9]|[2-9][0-9])" || {
  echo "Python 3.11+ required. Found: $(python3 --version)"
  exit 1
}

python3 -m venv .venv
. .venv/bin/activate

pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "Done. Environment ready."
echo "  Verify a repo's setup:  python lesson_code.py --path /path/to/cortex"
echo "  Run the tests:           pytest test_lesson.py -v"
echo ""
echo "To actually apply this lesson's repo setup to a fresh Cortex clone, run:"
echo '  mkdir -p .github && touch .gitignore'
echo '  printf ".env\n__pycache__/\n.venv/\n" > .gitignore'
echo '  printf "## What changed\n\n## Why\n\n## How it was tested\n" > .github/pull_request_template.md'
echo "  python lesson_code.py --path ."
