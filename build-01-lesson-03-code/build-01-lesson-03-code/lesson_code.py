"""
Cortex — Build 01, Lesson 03
Linux CLI & bash scripting — setup.sh, seed.sh, and dev tooling for the repo.

The bash scripts (seed.sh, doctor.sh) are this lesson's real deliverable.
This module is the other half of the concept: how a calling process should
treat a well-behaved script — capture output, never assume success, always
check the exit code. Today that caller is a Python harness. In Build 08 it's
a GitHub Actions job. In Build 10 it's a container entrypoint. The contract
these scripts expose doesn't change; only who's calling them does.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


def run_script(name: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a bash script and capture its result — never assume success."""
    script = SCRIPT_DIR / name
    return subprocess.run(
        ["bash", str(script), *args],
        capture_output=True,
        text=True,
    )


def run_doctor() -> bool:
    result = run_script("doctor.sh")
    print(result.stdout, end="")
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr, end="")
    return result.returncode == 0


def run_seed(data_dir: str) -> None:
    result = run_script("seed.sh", data_dir)
    print(result.stdout, end="")
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr, end="")
        raise RuntimeError(f"seed.sh failed with exit code {result.returncode}")


def main() -> int:
    print("Running dev environment check...\n")
    doctor_ok = run_doctor()

    data_dir = str(Path.cwd() / "data" / "documents")

    print("\nSeeding sample documents...\n")
    run_seed(data_dir)

    print("\nSeeding again — should be idempotent, not duplicate...\n")
    run_seed(data_dir)

    return 0 if doctor_ok else 1


if __name__ == "__main__":
    sys.exit(main())
