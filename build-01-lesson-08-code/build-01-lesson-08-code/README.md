# Cortex — Build 01 Milestone: Dockerized Document Management API

Seven lessons of individually-verified work, proven together. This isn't a
new feature — it's the checkpoint the entire Build has been working toward:
**clone this, run one command, and every endpoint built since Lesson 04
actually works.**

## What's in this package

Everything Build 01 shipped, consolidated:

| File | From | What it does |
|---|---|---|
| `.gitignore`, `.github/pull_request_template.md` | Lesson 01 | The Git discipline every lesson's PR followed |
| `doctor.sh` | Lesson 03 | Dev environment health check |
| `seed.sh` | Lesson 03 | Idempotent sample data |
| `lesson_code.py` | Lessons 02, 04–07 | FastAPI + Postgres + dedup + pagination + LRU cache |
| `schema.sql` | Lessons 05–06 | Documents, users, tags, dedup index, keyset pagination index |
| `Dockerfile`, `docker-compose.yml` | Lesson 07 | One-command startup |
| `test_lesson.py` | This lesson | A full happy-path smoke test, not per-feature unit tests |

## How this was actually verified

Same honesty as Lesson 07: this environment has no Docker daemon, so
`docker compose up` itself wasn't run here. What *was* run, twice, in two
different ways:

1. **The smoke test suite** (`pytest test_lesson.py -v`) — three tests, the
   main one walking a single continuous story: health check → create a
   user → create and tag a document → hit a 404 → hit dedup → create six
   more documents and page through all seven with no gaps or duplicates →
   confirm a cached re-fetch matches. All passing against real Postgres.
2. **A real running server**, hit with real `curl` calls in the same
   sequence a person would actually use — `doctor.sh`, then `seed.sh`, then
   `uvicorn`, then health check, user creation, seeded data, document
   creation with tags, dedup, and a 404 — all producing exactly the
   responses documented in this lesson's article.

Run `docker compose up --build` yourself to close the one gap this package
couldn't verify in this environment: the container build itself.

## Quick start

```bash
chmod +x setup.sh
./setup.sh
```

`setup.sh` runs `doctor.sh` first — if your machine is missing something
Build 01 needs, you'll know before Docker even gets involved.

Then:

```bash
./seed.sh ./data/documents
docker compose up --build
```

On WSL2, if `docker compose up` fails with a port 8000 error, copy
`.env.example` to `.env` and set `CORTEX_HOST_PORT=8888` (Windows often
reserves TCP 7964–8063, which includes 8000).

```bash
curl http://localhost:${CORTEX_HOST_PORT:-8000}/health
curl http://localhost:${CORTEX_HOST_PORT:-8000}/documents?owner_id=user-1
```

## Smoke tests (without Docker)

`setup.sh` creates `.venv` with the pinned test dependencies (`pytest`,
`pytest-asyncio`, etc.). Use that environment — the system `pytest` on
Ubuntu often lacks `pytest-asyncio` and ignores the `asyncio_*` options in
`pytest.ini`:

```bash
.venv/bin/pytest test_lesson.py -v
```

Requires Postgres on `localhost:5432` (or set `CORTEX_DATABASE_URL`). With
Docker Compose running, the bundled Postgres on port 5432 is enough.

## This lesson's git tag

```bash
git checkout build-01-lesson-08
```

This tag is Build 01, complete. Build 02 starts from here — Cortex gets its
first ML capability, an auto-classifier trained on the documents this exact
system now stores.
