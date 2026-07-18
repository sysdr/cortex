# Build 01, Lesson 03 — Linux CLI & bash scripting

Two real dev-tooling scripts, plus the Python discipline for calling them
correctly. `seed.sh` and `doctor.sh` are the actual deliverable; `lesson_code.py`
demonstrates how CI (Build 08) and a container entrypoint (Build 10) will
eventually invoke scripts exactly like these.

## What this proves

- `seed.sh` is idempotent — running it twice creates 0 new files the second
  time, not 3 duplicates (`test_seed_is_idempotent`).
- `doctor.sh` distinguishes required checks (python, git — fail the exit
  code) from optional ones (docker — warns, doesn't fail), because Docker
  isn't needed until Lesson 07.
- Both scripts follow the same contract: a clear summary line, a non-zero
  exit code on real failure, safe to call from anywhere via an absolute or
  relative path.

## Quick start

```bash
chmod +x setup.sh
./setup.sh

source .venv/bin/activate    # if not already active
./doctor.sh
./seed.sh ./data/documents
./seed.sh ./data/documents   # run again — should report created=0

python lesson_code.py
pytest test_lesson.py -v
```

Expected `doctor.sh` output:

```
Cortex dev environment check
----------------------------------------
[PASS] python3 >= 3.11
[PASS] git installed
[WARN] docker installed (not required until Build 01, Lesson 07)
----------------------------------------
All required checks passed.
```

Expected `seed.sh` output on a second run:

```
seed.sh: created=0 skipped=3 total=3
```

## This lesson's git tag

```bash
git checkout build-01-lesson-03
```

Builds on `build-01-lesson-02` (the async service layer). Nothing here wires
`seed.sh`'s output into `DocumentService` yet — that connection is made once
Postgres exists, in Lesson 05.
