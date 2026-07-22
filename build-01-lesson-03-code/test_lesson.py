"""
Tests for Build 01, Lesson 03.
Run with: pytest test_lesson.py -v

These invoke the real bash scripts through subprocess — the point of this
lesson is the scripts, not a Python re-implementation of them.
"""

import json
from pathlib import Path

from lesson_code import run_script


def test_seed_creates_three_documents(tmp_path: Path):
    result = run_script("seed.sh", str(tmp_path))

    assert result.returncode == 0
    assert len(list(tmp_path.glob("*.json"))) == 3


def test_seed_documents_have_required_fields(tmp_path: Path):
    run_script("seed.sh", str(tmp_path))

    for file in tmp_path.glob("*.json"):
        doc = json.loads(file.read_text())
        assert {"id", "title", "body", "owner_id"} <= doc.keys()


def test_seed_is_idempotent(tmp_path: Path):
    first = run_script("seed.sh", str(tmp_path))
    second = run_script("seed.sh", str(tmp_path))

    assert "created=3" in first.stdout
    assert "created=0 skipped=3" in second.stdout
    # still exactly 3 files on disk, not 6 — this is the actual concept
    assert len(list(tmp_path.glob("*.json"))) == 3


def test_seed_defaults_to_local_data_dir_when_no_arg_given(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = run_script("seed.sh")

    assert result.returncode == 0
    assert (tmp_path / "data" / "documents").is_dir()


def test_doctor_reports_each_check_by_name():
    result = run_script("doctor.sh")

    assert "python3 >= 3.11" in result.stdout
    assert "git installed" in result.stdout
    assert "docker installed" in result.stdout


def test_doctor_exit_code_reflects_required_checks_only():
    result = run_script("doctor.sh")

    # docker is a WARN, not a FAIL — required checks (python, git) are
    # expected to be present in this environment, so exit code is 0
    # regardless of whether docker happens to be installed.
    assert result.returncode == 0
