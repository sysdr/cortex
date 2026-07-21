-- Cortex — Build 01, Lesson 07
-- Docker & Docker Compose: Cortex API + Postgres, one `docker compose up`.
--
-- Unchanged from Lesson 06. This lesson doesn't touch the schema — it
-- changes how the database gets created and reached, not what's in it.

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

ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_hash TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_owner_hash
    ON documents (owner_id, content_hash);

DROP INDEX IF EXISTS idx_documents_owner_id;
CREATE INDEX IF NOT EXISTS idx_documents_owner_created_id
    ON documents (owner_id, created_at, id);
