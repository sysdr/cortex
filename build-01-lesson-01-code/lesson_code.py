"""
Cortex — Build 01, Lesson 01
Repo setup, Git branching model, and the PR/review discipline used for the
entire series.

Lesson 1 has no application code yet — what it has is a *discipline*: a repo
skeleton, a .gitignore that keeps secrets out of history, and a PR template
that every future lesson's PR will use. This script verifies that discipline
is actually in place, the same way a health-check endpoint will later verify
Cortex itself is in a good state (that's Build 09 — this is the same idea,
applied to the repo instead of the running service).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

REQUIRED_GITIGNORE_PATTERNS = [".env", "__pycache__/", ".venv/"]
REQUIRED_PR_TEMPLATE_SECTIONS = ["What changed", "Why", "How it was tested"]


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def check_git_initialized(repo_path: Path) -> CheckResult:
    exists = (repo_path / ".git").is_dir()
    return CheckResult(
        name="Git repo initialized",
        passed=exists,
        detail=".git/ found" if exists else "no .git/ directory — run `git init`",
    )


def check_gitignore_patterns(repo_path: Path) -> CheckResult:
    gitignore = repo_path / ".gitignore"
    if not gitignore.exists():
        return CheckResult("`.gitignore` present", False, "no .gitignore file found")

    content = gitignore.read_text()
    missing = [p for p in REQUIRED_GITIGNORE_PATTERNS if p not in content]

    if missing:
        return CheckResult(
            "`.gitignore` covers required patterns",
            False,
            f"missing patterns: {', '.join(missing)}",
        )
    return CheckResult(
        "`.gitignore` covers required patterns", True, "all required patterns present"
    )


def check_pr_template(repo_path: Path) -> CheckResult:
    template = repo_path / ".github" / "pull_request_template.md"
    if not template.exists():
        return CheckResult(
            "PR template present", False, "no .github/pull_request_template.md found"
        )

    content = template.read_text()
    missing = [s for s in REQUIRED_PR_TEMPLATE_SECTIONS if s not in content]

    if missing:
        return CheckResult(
            "PR template covers required sections",
            False,
            f"missing sections: {', '.join(missing)}",
        )
    return CheckResult(
        "PR template covers required sections", True, "all required sections present"
    )


def run_all_checks(repo_path: Path) -> list[CheckResult]:
    return [
        check_git_initialized(repo_path),
        check_gitignore_patterns(repo_path),
        check_pr_template(repo_path),
    ]


def _print_report(results: list[CheckResult]) -> bool:
    all_passed = True
    print("\nCortex repo setup check\n" + "-" * 40)
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        if not r.passed:
            all_passed = False
        print(f"[{status}] {r.name}\n       {r.detail}")
    print("-" * 40)
    print("All checks passed." if all_passed else "Some checks failed — see above.")
    return all_passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Cortex repo setup discipline.")
    parser.add_argument(
        "--path", default=".", help="path to the repo root (default: current directory)"
    )
    args = parser.parse_args()

    results = run_all_checks(Path(args.path).resolve())
    ok = _print_report(results)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
