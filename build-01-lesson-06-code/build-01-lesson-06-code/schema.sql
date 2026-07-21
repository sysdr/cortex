-- Cortex — Build 01, Lesson 06
-- DSA in context: efficient pagination, dedup, and an LRU cache.
--
-- The base tables below are unchanged from Lesson 05 — copied forward, not
-- rewritten, because rewriting them to include today's new column would
-- misrepresent what Lesson 05 actually shipped. Today's changes are
-- explicit ALTER statements underneath, which is the honest way to evolve
-- a schema that might already exist with real rows in it.

CREATE TABLE IF NOT EXISTS users (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email        TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    owner_id   TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tags (
    id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS document_tags (
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    tag_id      UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (document_id, tag_id)
);

-- ── Build 01, Lesson 06 — dedup + efficient pagination ──────────────────

-- CREATE TABLE IF NOT EXISTS only helps on day one. A table that already
-- exists — with real rows in it — needs ALTER TABLE ADD COLUMN IF NOT
-- EXISTS instead, which is safe to run whether documents is brand new or
-- already has data. Left nullable on purpose: giving existing rows a real
-- content_hash would need a backfill pass, which is a bigger job than one
-- lesson (it's Build 09 territory) — new rows always get one going forward.
ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_hash TEXT;

-- Enforces dedup at the database level, not just in application code: two
-- INSERTs racing each other with identical content can't both succeed,
-- because Postgres itself rejects the second one.
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_owner_hash
    ON documents (owner_id, content_hash);

-- Lesson 05's single-column index only ever served "WHERE owner_id = X."
-- This composite index serves that *and* the keyset pagination predicate
-- below — a query filtering on owner_id alone can still use it, because a
-- B-tree index is usable by any leftmost prefix of its columns, not just
-- the full column list.
DROP INDEX IF EXISTS idx_documents_owner_id;
CREATE INDEX IF NOT EXISTS idx_documents_owner_created_id
    ON documents (owner_id, created_at, id);
