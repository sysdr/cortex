# Build 01, Lesson 05 — SQL & schema design: Postgres

`DocumentService`'s internals change for the first time since Lesson 02 — an
in-memory dict becomes real Postgres, with proper ownership and a
many-to-many tags model. Its public methods (`create_document`,
`get_document`, `list_documents`) don't change shape at all.

## What this proves

- `schema.sql` is idempotent — `CREATE TABLE IF NOT EXISTS` everywhere, the
  same discipline `seed.sh` (Lesson 03) applied to data.
- Tags are a separate table joined through `document_tags`, so two
  documents sharing a tag produce exactly one `tags` row, not two
  (`test_shared_tags_deduplicate_to_one_row`).
- A malformed document ID (not even a valid UUID) returns `None`, the same
  as a valid-but-missing ID — a caller never needs to know our primary key
  type to get a sane "not found."

## Quick start

This lesson needs a real Postgres reachable at
`postgresql://postgres:postgres@127.0.0.1:5432/cortex` (override with the
`CORTEX_DATABASE_URL` environment variable). `setup.sh` prints the commands
to stand one up locally if you don't have one yet — we're doing this by
hand on purpose this lesson; Lesson 07 automates it with Docker Compose.

```bash
chmod +x setup.sh
./setup.sh

source .venv/bin/activate    # if not already active
python lesson_code.py        # applies schema.sql, runs a demo
pytest test_lesson.py -v
```

Expected demo output (UUIDs will differ):

```
Created: Document(id='...', title='Q3 Roadmap', body='Draft roadmap.', owner_id='user-1', tags=('planning', 'q3'))
Fetched: Document(id='...', title='Q3 Roadmap', body='Draft roadmap.', owner_id='user-1', tags=('planning', 'q3'))

user-1 has 2 documents:
  - Q3 Roadmap  tags=('planning', 'q3')
  - Onboarding Notes  tags=('planning',)
```

## This lesson's git tag

```bash
git checkout build-01-lesson-05
```

Builds on `build-01-lesson-04` (the FastAPI app). Lesson 04's endpoints
don't need to change at all — only what `get_document_service()` returns
does, once this `DocumentService` is wired in behind it.
