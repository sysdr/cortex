# Build 01, Lesson 06 — DSA in context: pagination, dedup, LRU cache

Three data-structure ideas applied to the exact `DocumentService` that's
been running since Lesson 02. This is also the first lesson where the
service's public shape genuinely changes — `list_documents` now returns a
`Page`, not a bare `list[Document]`.

## What this proves

- **Dedup**: two `create_document` calls with identical title+body for the
  same owner return the same document, and only one row ever lands in
  Postgres (`test_identical_content_from_same_owner_dedups`).
- **Keyset pagination**: walking every page from `list_documents` visits
  every document exactly once — no gaps, no duplicates — which is the real
  correctness bar for pagination, not just "it returns some rows"
  (`test_pagination_walks_every_document_exactly_once`).
- **LRU cache**: a second `get_document` call for the same ID is a cache
  hit, and the least-recently-used entry is evicted once the cache exceeds
  its capacity (`test_lru_evicts_least_recently_used_beyond_capacity`).

## Quick start

Same Postgres instance as Lesson 05. This lesson's `schema.sql` is safe to
run against Lesson 05's existing tables — it uses `ALTER TABLE ... ADD
COLUMN IF NOT EXISTS`, not just `CREATE TABLE IF NOT EXISTS`, so it evolves
a database that already has data instead of silently doing nothing.

```bash
chmod +x setup.sh
./setup.sh

source .venv/bin/activate    # if not already active
python lesson_code.py        # applies schema.sql, runs all three demos
pytest test_lesson.py -v
```

Expected demo output (values will vary):

```
--- Dedup demo ---
Same id returned for identical content: True

--- Pagination demo (page size 2) ---
Page 1: ['Doc 0', 'Doc 1']  next_cursor=True
Page 2: ['Doc 2', 'Doc 3']  next_cursor=True

--- LRU cache demo (capacity=2) ---
cache_info after warm access: {'hits': 1, 'misses': 0, 'size': 2}
```

## This lesson's git tag

```bash
git checkout build-01-lesson-06
```

Builds on `build-01-lesson-05` (Postgres, tags). Note for anyone wiring this
into Lesson 04's FastAPI app: the `/documents` list endpoint needs a small
update to accept `limit`/`cursor` query params and return the new `Page`
shape — that's a genuine breaking change, not one this lesson hides.
