# Build 01, Lesson 07 — Docker & Docker Compose

Everything done by hand since Lesson 05 — install Postgres, set a password,
create a database — becomes `docker-compose.yml`. And Lesson 06's flagged
breaking change (`list_documents` returning `Page`, not a bare list) finally
gets applied to the FastAPI endpoint, deliberately, not silently.

## How this was actually verified

Being direct about this: the sandbox this package was built in doesn't have
a Docker daemon available, so `docker compose up` itself couldn't be run
here. What *was* verified, rigorously:

- The exact application code (`lesson_code.py`) — the same file the
  container runs — was tested against a real Postgres instance, both
  through `pytest` (8/8 passing) and through a real running `uvicorn`
  server hit with real `curl` calls (health check, seeded data, dedup
  through the HTTP layer, pagination cursors, 404s — all confirmed).
- `docker-compose.yml` was validated as syntactically correct YAML with
  the expected service structure (`postgres` + `api`, healthcheck,
  `depends_on: condition: service_healthy`, volumes).
- The `Dockerfile` was reviewed by hand for correctness (layer ordering,
  `EXPOSE`, `CMD`) but not built.

Run `docker compose up --build` yourself to complete the loop this package
couldn't close in this environment. If something doesn't work, the
application logic itself is the least likely culprit — it's proven.

## What this proves

- A found-and-fixed real bug, kept in rather than smoothed over: an early
  version of this lesson's tests passed a Postgres connection pool created
  in one event loop into `TestClient`, which runs its own event loop
  internally — asyncpg pools are bound to the loop they're created on, and
  this broke immediately. The fix: `create_app()` never accepts an
  external pool: it always creates and owns one, which is also exactly how
  the real container behaves.
- Seeding is idempotent across restarts for free, because it goes through
  `create_document` — which already dedups — instead of a raw insert
  (`test_seed_loading_is_idempotent_across_restarts`).

## Quick start

```bash
chmod +x setup.sh
./setup.sh
```

### Path A — Docker Compose (what this lesson is about)

```bash
./start.sh
```

Or manually:

```bash
./seed.sh ./data/documents
docker compose up --build -d    # -d keeps containers running in the background
```

In another terminal:

```bash
curl http://localhost:8888/health
curl "http://localhost:8888/documents?owner_id=user-1"
```

On WSL/Docker Desktop, host port **8000** is often blocked by Windows, so the
API is published on **8888** instead. Port 8000 is only used inside the
container. If you run `docker compose up` without `-d`, keep that terminal
open — Ctrl+C or closing it stops Postgres and the API (exit code 0 is normal).

```bash
docker compose down       # stop
docker compose down -v    # stop and wipe the Postgres volume too
```

### Path B — local uvicorn on port 8000 (WSL-friendly)

Runs Postgres in Docker but the API via your project venv — avoids the
Windows port-8000 block for Docker:

```bash
./dev.sh
```

In another terminal:

```bash
curl http://localhost:8000/health
source .venv/bin/activate
pytest test_lesson.py -v
```

### Verify everything

```bash
./verify.sh
```

## This lesson's git tag

```bash
git checkout build-01-lesson-07
```

Builds on `build-01-lesson-06`. This is also the last lesson before Build
01's milestone (Lesson 08): a fresh clone, `docker compose up`, and every
endpoint built since Lesson 04 is live.
