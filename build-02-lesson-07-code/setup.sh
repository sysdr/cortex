#!/usr/bin/env bash
# Cortex — Build 02, Lesson 07 (Build Milestone) — environment setup
set -euo pipefail

echo "Cortex — Build 02 Milestone setup"
echo ""

python3 --version | grep -qE "3\.(1[1-9]|[2-9][0-9])" || {
  echo "Python 3.11+ required. Found: $(python3 --version)"
  exit 1
}

python3 -m venv .venv
. .venv/bin/activate

pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "Training the bootstrap classifier (synthetic data — see README)..."
python train_classifier.py

echo ""
echo "Done. This lesson needs Postgres reachable at:"
echo "  postgresql://postgres:postgres@127.0.0.1:5432/cortex"
echo "(see Build 01, Lesson 05's setup.sh if you don't have one running)"
echo ""
echo "  Activate env:  source .venv/bin/activate"
echo "  Run the API:   uvicorn lesson_code:app --reload"
echo "  Run the tests: ./test.sh -v"
