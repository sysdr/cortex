#!/usr/bin/env bash
# Cortex — Build 02, Lesson 06 — environment setup
set -euo pipefail

echo "Setting up Build 02, Lesson 06 environment..."
echo "Note: installing CPU-only torch (this lesson runs on cpu)."

python3 --version | grep -qE "3\.(1[1-9]|[2-9][0-9])" || {
  echo "Python 3.11+ required. Found: $(python3 --version)"
  exit 1
}

python3 -m venv .venv
. .venv/bin/activate

pip install --upgrade pip -q
# Install torch from the CPU index so pip does not pull multi-GB CUDA wheels
# (nvidia-cudnn, cusparselt, etc.) that often time out on flaky networks.
pip install numpy==2.1.3 pytest==8.3.3
# Remove any prior torch install (CUDA wheels can leave cu130 binaries behind
# while metadata says +cpu, causing libcudart.so import failures).
pip uninstall -y torch 2>/dev/null || true
rm -rf .venv/lib/python3.12/site-packages/torch \
       .venv/lib/python3.12/site-packages/torch-*.dist-info \
       .venv/lib/python3.12/site-packages/functorch \
       .venv/lib/python3.12/site-packages/torchgen
pip install torch==2.13.0 \
  --index-url https://download.pytorch.org/whl/cpu \
  --resume-retries 50 \
  --timeout 120

echo ""
echo "Done. Environment ready. No database needed for this lesson."
echo "  Run the demo:  python lesson_code.py"
echo "  Run the tests: pytest test_lesson.py -v"
