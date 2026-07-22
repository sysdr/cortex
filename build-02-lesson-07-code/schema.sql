-- Cortex — Build 02, Lesson 07 (Build Milestone)
-- /classify endpoint: every document uploaded to Cortex gets auto-tagged
-- by a model you trained.
--
-- Base tables unchanged from Build 01. Today's addition: a category
-- column, populated automatically by the classifier at document-creation
-- time — the same ALTER TABLE ADD COLUMN IF NOT EXISTS discipline Build
-- 01, Lesson 06 established for evolving a live schema.

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

-- Build 02, Lesson 07 — the classifier's output lives on the document row.
-- Nullable: documents created before the classifier existed, or created
-- while classification is unavailable, still have to be valid rows.
ALTER TABLE documents ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS category_confidence REAL;
