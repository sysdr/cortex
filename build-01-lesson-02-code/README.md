# Build 01, Lesson 02 — Python async, decorators & type hints

Cortex's service layer, isolated. No FastAPI, no Postgres yet — those land in
Lessons 04 and 05, on top of this tag.

## What this proves

- `DocumentService` is async end-to-end and safe under real concurrency
  (see `test_concurrent_creates_do_not_lose_writes`).
- `@log_call` wraps any async method with timing/logging without changing its
  signature or swallowing exceptions — the same pattern Build 09 uses for
  LLM-call tracing.
- `Document` is a frozen dataclass — precise, immutable, and cheap to reason
  about once caching (Build 09) and multi-tenancy (Build 10.5) show up.

## Quick start

```bash
chmod +x setup.sh
./setup.sh

source .venv/bin/activate
python lesson_code.py      # runs the demo
pytest test_lesson.py -v   # runs the tests
```

Expected demo output (UUIDs will differ):

```
[log_call] create_document ok in 0.03ms
[log_call] create_document ok in 0.02ms
[log_call] create_document ok in 0.02ms
[log_call] list_documents ok in 0.01ms

user-1 has 2 documents:
  - Q3 Roadmap (a1b2c3d4...)
  - Onboarding Notes (e5f6a7b8...)

[log_call] get_document ok in 0.00ms

Looking up a missing document returns: None
```

## This lesson's git tag

```bash
git checkout build-01-lesson-02
```

Builds directly on `build-01-lesson-01` (repo skeleton + Git workflow). Nothing
here depends on a future lesson.
