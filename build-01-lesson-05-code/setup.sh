#!/usr/bin/env bash
# Cortex — Build 01, Lesson 05 — environment setup
set -euo pipefail

echo "Setting up Lesson 05 environment..."

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
echo "This lesson needs a real Postgres reachable at:"
echo "  postgresql://postgres:postgres@127.0.0.1:5432/cortex"
echo "(override with CORTEX_DATABASE_URL if yours differs)"
echo ""
echo "If you don't have Postgres running yet:"
echo "  sudo apt-get install -y postgresql postgresql-contrib"
echo "  sudo service postgresql start"
echo "  sudo -u postgres psql -c \"ALTER USER postgres PASSWORD 'postgres';\""
echo "  sudo -u postgres psql -c \"CREATE DATABASE cortex;\""
echo ""
echo "We're doing this by hand today, on purpose — Lesson 07's"
echo "'docker compose up' will feel like solving a problem you've"
echo "actually felt, not an abstract convenience."
echo ""
echo "  Run the demo:  python lesson_code.py"
echo "  Run the tests: pytest test_lesson.py -v"
