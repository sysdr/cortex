# Build 01, Lesson 01 — Repo setup & Git workflow

The discipline this whole series runs on: a repo skeleton, a `.gitignore` that
keeps secrets out of history, and a PR template every future lesson reuses.
This package is a small tool that verifies that discipline is actually in
place — not application code, since Cortex doesn't have any yet.

## What this proves

- `run_all_checks()` verifies git is initialized, `.gitignore` covers the
  required patterns, and the PR template has all three required sections —
  the same "verify the environment is healthy" instinct Build 09 applies to
  the running service instead of the repo.
- Every check is isolated and testable against a fake repo in a temp
  directory, not against this actual repo — so the tests don't depend on
  where you happen to run them from.

## Quick start

```bash
chmod +x setup.sh
./setup.sh

# check any repo's setup (defaults to current directory)
python lesson_code.py --path .

# run the tests
pytest test_lesson.py -v
```

Expected output against a correctly set-up repo:

```
Cortex repo setup check
----------------------------------------
[PASS] Git repo initialized
       .git/ found
[PASS] `.gitignore` covers required patterns
       all required patterns present
[PASS] PR template covers required sections
       all required sections present
----------------------------------------
All checks passed.
```

## This lesson's git tag

```bash
git checkout build-01-lesson-01
```

The first tag in the series — everything after this builds on top of it.
