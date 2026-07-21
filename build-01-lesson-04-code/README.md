# Build 01, Lesson 04 — FastAPI: `/documents` and `/users`

Lesson 02's `DocumentService` gets an HTTP face. Lesson 03's `seed.sh` output
becomes the first thing you can `curl` out of a running Cortex. No Postgres
yet — that's Lesson 05; this is still the in-memory store, just reachable
over HTTP now.

## What this proves

- `create_app(data_dir=...)` builds a fully isolated FastAPI app per call —
  no shared state between tests, no shared state between a real run and a
  test run.
- The app's `lifespan` loads any `seed.sh`-produced JSON files at startup,
  idempotently, the same way `seed.sh` itself is idempotent
  (`test_startup_loads_seeded_documents_from_disk`).
- A missing document or user returns a real `404`, not a `200` with an empty
  body — the HTTP-layer equivalent of Lesson 01's "say exactly what's wrong."

## Quick start

```bash
chmod +x setup.sh
./setup.sh

source .venv/bin/activate    # if not already active
./seed.sh ./data/documents
uvicorn lesson_code:app --reload
```

In another terminal:

```bash
curl http://127.0.0.1:8000/documents?owner_id=user-1
# [{"id":"...","title":"Q3 Roadmap", ...}, {"id":"...","title":"Onboarding Notes", ...}]

curl -X POST http://127.0.0.1:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"title":"New Doc","body":"hello","owner_id":"user-1"}'
# 201 {"id":"...","title":"New Doc", ...}

curl http://127.0.0.1:8000/documents/does-not-exist
# 404 {"detail":"Document not found"}
```

FastAPI's interactive docs are free at `http://127.0.0.1:8000/docs` — worth
opening once, since Build 04 relies on this same schema for function calling.

Run the tests:

```bash
pytest test_lesson.py -v
```

## This lesson's git tag

```bash
git checkout build-01-lesson-04
```

Builds on `build-01-lesson-03` (`seed.sh`, `doctor.sh`) and, further back,
`build-01-lesson-02` (`DocumentService`, `log_call`). Nothing here touches a
real database — that's Lesson 05, and the service method signatures won't
need to change when it lands.
