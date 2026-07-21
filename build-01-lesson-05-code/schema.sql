-- Cortex — Build 01, Lesson 05
-- SQL & schema design: modeling documents, ownership, and tags.
--
-- Idempotent by design (IF NOT EXISTS everywhere) — the same discipline
-- Lesson 03's seed.sh established for scripts applies to schema setup too.

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
    owner_id   TEXT NOT NULL,  -- not a foreign key yet: Lesson 04's users
                                -- are still in-memory. Tightened once
                                -- UserService moves to Postgres too.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per unique tag name — "urgent" exists exactly once no matter how
-- many documents use it. This is *why* tags are a separate table instead of
-- a text column on documents: without it, renaming a tag means rewriting
-- every document that has it.
CREATE TABLE IF NOT EXISTS tags (
    id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE
);

-- The join table: a document can have many tags, a tag can apply to many
-- documents. This many-to-many shape is the reason a third table exists at
-- all — neither documents nor tags alone can represent it.
CREATE TABLE IF NOT EXISTS document_tags (
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    tag_id      UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (document_id, tag_id)
);

-- Every document lookup in this lesson filters by owner_id — this index is
-- what keeps list_documents() fast as the table grows past a few rows,
-- instead of forcing a full table scan on every call.
CREATE INDEX IF NOT EXISTS idx_documents_owner_id ON documents (owner_id);
