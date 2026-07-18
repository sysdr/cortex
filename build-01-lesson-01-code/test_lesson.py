"""
Tests for Build 01, Lesson 01.
Run with: pytest test_lesson.py -v

These build a fake repo skeleton in a temp directory for each test, so the
checks are verified in isolation from this actual Cortex repo.
"""

from pathlib import Path

from lesson_code import (
    check_git_initialized,
    check_gitignore_patterns,
    check_pr_template,
    run_all_checks,
)


def test_check_git_initialized_true(tmp_path: Path):
    (tmp_path / ".git").mkdir()

    result = check_git_initialized(tmp_path)

    assert result.passed


def test_check_git_initialized_false(tmp_path: Path):
    result = check_git_initialized(tmp_path)

    assert not result.passed


def test_check_gitignore_passes_with_all_patterns(tmp_path: Path):
    (tmp_path / ".gitignore").write_text(".env\n__pycache__/\n.venv/\n")

    result = check_gitignore_patterns(tmp_path)

    assert result.passed


def test_check_gitignore_fails_when_env_missing(tmp_path: Path):
    (tmp_path / ".gitignore").write_text("__pycache__/\n.venv/\n")

    result = check_gitignore_patterns(tmp_path)

    assert not result.passed
    assert ".env" in result.detail


def test_check_gitignore_fails_when_file_missing(tmp_path: Path):
    result = check_gitignore_patterns(tmp_path)

    assert not result.passed


def test_check_pr_template_passes_with_all_sections(tmp_path: Path):
    github_dir = tmp_path / ".github"
    github_dir.mkdir()
    (github_dir / "pull_request_template.md").write_text(
        "## What changed\n\n## Why\n\n## How it was tested\n"
    )

    result = check_pr_template(tmp_path)

    assert result.passed


def test_check_pr_template_fails_when_section_missing(tmp_path: Path):
    github_dir = tmp_path / ".github"
    github_dir.mkdir()
    (github_dir / "pull_request_template.md").write_text("## What changed\n\n## Why\n")

    result = check_pr_template(tmp_path)

    assert not result.passed
    assert "How it was tested" in result.detail


def test_run_all_checks_on_a_fully_correct_repo(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitignore").write_text(".env\n__pycache__/\n.venv/\n")
    github_dir = tmp_path / ".github"
    github_dir.mkdir()
    (github_dir / "pull_request_template.md").write_text(
        "## What changed\n\n## Why\n\n## How it was tested\n"
    )

    results = run_all_checks(tmp_path)

    assert all(r.passed for r in results)
    assert len(results) == 3
