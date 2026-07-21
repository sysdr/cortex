"""
Cortex — Build 01, Lesson 05
SQL & schema design: modeling documents, ownership, and tags in Postgres.

DocumentService keeps the exact same public method signatures as Lesson 02
and Lesson 04 — create_document, get_document, list_documents. Only what's
behind them changes: asyncpg and real SQL instead of an in-memory dict.
Every FastAPI endpoint from Lesson 04 works against this class unmodified —
that's the entire point of the service-layer boundary established on Day 2.
"""

from __future__ import annotations

import functools
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, TypeVar

import asyncpg

T = TypeVar("T")

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
DEFAULT_DSN = "postgresql://postgres:postgres@127.0.0.1:5432/cortex"


def log_call(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """Unchanged from Lesson 02 — the decorator doesn't care what's inside
    the function it wraps, which is exactly why it still works here."""

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs) -> T:
        start = time.perf_counter()
        try:
            result = await fn(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            print(f"[log_call] {fn.__name__} ok in {elapsed_ms:.2f}ms")
            return result
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            print(f"[log_call] {fn.__name__} FAILED in {elapsed_ms:.2f}ms: {exc}")
            raise

    return wrapper


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    title: str
    body: str
    owner_id: str
    tags: tuple[str, ...] = ()


async def create_pool(dsn: str | None = None) -> asyncpg.Pool:
    dsn = dsn or os.environ.get("CORTEX_DATABASE_URL", DEFAULT_DSN)
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


async def apply_schema(pool: asyncpg.Pool) -> None:
    """Idempotent, the same way Lesson 03's seed.sh is idempotent — every
    statement in schema.sql is CREATE ... IF NOT EXISTS, so calling this
    against an already-set-up database is a safe no-op."""
    sql = SCHEMA_PATH.read_text()
    async with pool.acquire() as conn:
        await conn.execute(sql)


class DocumentService:
    """Same public contract as Lesson 02 / Lesson 04's DocumentService, now
    backed by Postgres. Anything depending on Depends(get_document_service)
    in Lesson 04's FastAPI app keeps working without a single line change."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @log_call
    async def create_document(
        self,
        title: str,
        body: str,
        owner_id: str,
        tags: list[str] | None = None,
    ) -> Document:
        tags = tags or []
        async with self._pool.acquire() as conn, conn.transaction():
            row = await conn.fetchrow(
                """
                INSERT INTO documents (title, body, owner_id)
                VALUES ($1, $2, $3)
                RETURNING id, title, body, owner_id
                """,
                title, body, owner_id,
            )
            for tag_name in tags:
                # ON CONFLICT here is what makes two documents sharing a
                # tag end up pointing at one tags row, not two — this is
                # the payoff of tags being their own table.
                tag_id = await conn.fetchval(
                    """
                    INSERT INTO tags (name) VALUES ($1)
                    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """,
                    tag_name,
                )
                await conn.execute(
                    """
                    INSERT INTO document_tags (document_id, tag_id)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING
                    """,
                    row["id"], tag_id,
                )
        return Document(
            id=str(row["id"]), title=row["title"], body=row["body"],
            owner_id=row["owner_id"], tags=tuple(tags),
        )

    @log_call
    async def get_document(self, document_id: str) -> Document | None:
        async with self._pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    """
                    SELECT d.id, d.title, d.body, d.owner_id,
                           COALESCE(array_agg(t.name) FILTER (WHERE t.name IS NOT NULL), '{}') AS tags
                    FROM documents d
                    LEFT JOIN document_tags dt ON dt.document_id = d.id
                    LEFT JOIN tags t ON t.id = dt.tag_id
                    WHERE d.id = $1::uuid
                    GROUP BY d.id
                    """,
                    document_id,
                )
            except asyncpg.DataError:
                # document_id wasn't even a valid UUID — same contract as
                # "not found," not a 500. A caller shouldn't need to know
                # our primary key type to get a sane 404.
                return None

        if row is None:
            return None
        return Document(
            id=str(row["id"]), title=row["title"], body=row["body"],
            owner_id=row["owner_id"], tags=tuple(row["tags"]),
        )

    @log_call
    async def list_documents(self, owner_id: str) -> list[Document]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT d.id, d.title, d.body, d.owner_id,
                       COALESCE(array_agg(t.name) FILTER (WHERE t.name IS NOT NULL), '{}') AS tags
                FROM documents d
                LEFT JOIN document_tags dt ON dt.document_id = d.id
                LEFT JOIN tags t ON t.id = dt.tag_id
                WHERE d.owner_id = $1
                GROUP BY d.id
                ORDER BY d.created_at
                """,
                owner_id,
            )
        return [
            Document(
                id=str(r["id"]), title=r["title"], body=r["body"],
                owner_id=r["owner_id"], tags=tuple(r["tags"]),
            )
            for r in rows
        ]


async def _demo() -> None:
    pool = await create_pool()
    await apply_schema(pool)
    service = DocumentService(pool)

    doc = await service.create_document(
        "Q3 Roadmap", "Draft roadmap.", owner_id="user-1", tags=["planning", "q3"]
    )
    print(f"\nCreated: {doc}")

    fetched = await service.get_document(doc.id)
    print(f"Fetched: {fetched}")

    await service.create_document(
        "Onboarding Notes", "...", owner_id="user-1", tags=["planning"]
    )
    docs = await service.list_documents(owner_id="user-1")
    print(f"\nuser-1 has {len(docs)} documents:")
    for d in docs:
        print(f"  - {d.title}  tags={d.tags}")

    await pool.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(_demo())
