"""Pytest hooks shared by this lesson's test suite."""

import sys
from pathlib import Path


def pytest_configure(config):
    in_project_venv = Path(sys.prefix).resolve() == (Path(__file__).parent / ".venv").resolve()
    if sys.prefix == sys.base_prefix or not in_project_venv:
        import pytest

        pytest.exit(
            "Tests must run inside this project's virtualenv.\n\n"
            "  source .venv/bin/activate\n"
            "  pytest test_lesson.py -v\n\n"
            "Or run: ./test.sh -v\n\n"
            "If .venv is missing, run ./setup.sh first.",
            returncode=1,
        )
