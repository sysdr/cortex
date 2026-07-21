"""
Cortex — Build 01, Lesson 06
DSA in context: efficient pagination, dedup, and an LRU cache for hot documents.

Three data-structure ideas, applied to the exact service that's been
running since Lesson 02:

  - A hash (content_hash) turns "does this document already exist?" from
    an O(n) scan into an O(1) index lookup, enforced by Postgres itself.
  - Keyset pagination replaces OFFSET, which gets slower with every page,
    with a comparison the composite index answers directly.
  - An LRU cache (hash map + access-order eviction) keeps repeatedly
    requested documents out of the database entirely.

This is also the first lesson in the series where the service's public
shape genuinely changes — list_documents' return type is different today.
That's called out explicitly below, not hidden.
"""

from __future__ import annotations

import functools
import hashlib
import os
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, TypeVar

import asyncpg

T = TypeVar("T")

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
DEFAULT_DSN = "postgresql://postgres:postgres@127.0.0.1:5432/cortex"


def log_call(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """Unchanged since Lesson 02."""

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


@dataclass(frozen=True, slots=True)
class Page:
    """The new return shape for list_documents. Deliberately not hidden
    behind the old `list[Document]` signature — a page needs to say
    whether there's more, and pretending otherwise would just move that
    problem onto every caller."""

    items: list[Document]
    next_cursor: str | None


# ── LRU cache — hash map + access order, the two ingredients an LRU needs ─


class LRUCache:
    """A capacity-bounded cache: O(1) get and put, evicts the
    least-recently-used entry when full. `OrderedDict` gives us both
    ingredients for free — it's a hash map (O(1) lookup by key) that also
    remembers insertion/access order (O(1) move-to-end and pop-oldest),
    which is exactly the combination an LRU policy needs."""

    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self.hits = 0
        self.misses = 0
        self._store: OrderedDict[str, Document] = OrderedDict()

    def get(self, key: str) -> Document | None:
        if key not in self._store:
            self.misses += 1
            return None
        self._store.move_to_end(key)
        self.hits += 1
        return self._store[key]

    def put(self, key: str, value: Document) -> None:
        self._store[key] = value
        self._store.move_to_end(key)
        if len(self._store) > self.capacity:
            self._store.popitem(last=False)  # evict least recently used


# ── Cursor encoding — opaque tokens, not raw exposed internals ────────────


def _encode_cursor(created_at: datetime, doc_id: str) -> str:
    raw = f"{created_at.isoformat()}|{doc_id}"
    return urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    raw = urlsafe_b64decode(cursor.encode()).decode()
    ts_str, doc_id = raw.split("|", 1)
    return datetime.fromisoformat(ts_str), doc_id


async def create_pool(dsn: str | None = None) -> asyncpg.Pool:
    dsn = dsn or os.environ.get("CORTEX_DATABASE_URL", DEFAULT_DSN)
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


async def apply_schema(pool: asyncpg.Pool) -> None:
    sql = SCHEMA_PATH.read_text()
    async with pool.acquire() as conn:
        await conn.execute(sql)


class DocumentService:
    def __init__(self, pool: asyncpg.Pool, cache_capacity: int = 100) -> None:
        self._pool = pool
        self._cache = LRUCache(cache_capacity)

    def cache_info(self) -> dict[str, int]:
        return {
            "hits": self._cache.hits,
            "misses": self._cache.misses,
            "size": len(self._cache._store),
        }

    @log_call
    async def create_document(
        self,
        title: str,
        body: str,
        owner_id: str,
        tags: list[str] | None = None,
    ) -> Document:
        tags = tags or []
        # A hash turns "have we seen this exact content before?" into an
        # O(1) index lookup instead of comparing this document against
        # every other document this owner has.
        content_hash = hashlib.sha256(f"{title}\n{body}".encode()).hexdigest()

        async with self._pool.acquire() as conn, conn.transaction():
            row = await conn.fetchrow(
                """
                INSERT INTO documents (title, body, owner_id, content_hash)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (owner_id, content_hash) DO NOTHING
                RETURNING id, title, body, owner_id
                """,
                title, body, owner_id, content_hash,
            )
            is_new = row is not None

            if row is None:
                # Dedup hit — same owner, identical title+body already
                # exists. We don't create a duplicate; we return the
                # existing document instead.
                row = await conn.fetchrow(
                    """
                    SELECT id, title, body, owner_id FROM documents
                    WHERE owner_id = $1 AND content_hash = $2
                    """,
                    owner_id, content_hash,
                )

            if is_new:
                for tag_name in tags:
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
                final_tags: tuple[str, ...] = tuple(tags)
            else:
                # Ignore the tags argument this call — the dedup hit means
                # the existing document's tags are the source of truth.
                tag_rows = await conn.fetch(
                    """
                    SELECT t.name FROM tags t
                    JOIN document_tags dt ON dt.tag_id = t.id
                    WHERE dt.document_id = $1
                    """,
                    row["id"],
                )
                final_tags = tuple(r["name"] for r in tag_rows)

        doc = Document(
            id=str(row["id"]), title=row["title"], body=row["body"],
            owner_id=row["owner_id"], tags=final_tags,
        )
        self._cache.put(doc.id, doc)
        return doc

    @log_call
    async def get_document(self, document_id: str) -> Document | None:
        cached = self._cache.get(document_id)
        if cached is not None:
            return cached

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
                return None

        if row is None:
            return None

        doc = Document(
            id=str(row["id"]), title=row["title"], body=row["body"],
            owner_id=row["owner_id"], tags=tuple(row["tags"]),
        )
        self._cache.put(doc.id, doc)
        return doc

    @log_call
    async def list_documents(
        self, owner_id: str, *, limit: int = 20, cursor: str | None = None
    ) -> Page:
        """Keyset pagination, not OFFSET. OFFSET N asks Postgres to
        generate and discard the first N rows on every page — cheap on
        page 2, and increasingly expensive by page 200. Keyset pagination
        instead asks 'give me rows after this exact point,' which the
        composite index in schema.sql answers directly, doing roughly the
        same amount of work no matter how deep the page is.

        NOTE: this is the first lesson where the return type changes —
        list[Document] becomes Page. Lesson 04's FastAPI endpoint would
        need a small update to accept limit/cursor and return this new
        shape. That's a deliberate, visible contract change, not one
        hidden behind the old signature."""
        after_created_at: datetime | None = None
        after_id: str | None = None
        if cursor is not None:
            after_created_at, after_id = _decode_cursor(cursor)

        base_select = """
            SELECT d.id, d.title, d.body, d.owner_id, d.created_at,
                   COALESCE(array_agg(t.name) FILTER (WHERE t.name IS NOT NULL), '{}') AS tags
            FROM documents d
            LEFT JOIN document_tags dt ON dt.document_id = d.id
            LEFT JOIN tags t ON t.id = dt.tag_id
        """

        async with self._pool.acquire() as conn:
            if cursor is None:
                rows = await conn.fetch(
                    base_select + """
                    WHERE d.owner_id = $1
                    GROUP BY d.id
                    ORDER BY d.created_at, d.id
                    LIMIT $2
                    """,
                    owner_id, limit + 1,  # fetch one extra to detect "more"
                )
            else:
                rows = await conn.fetch(
                    base_select + """
                    WHERE d.owner_id = $1 AND (d.created_at, d.id) > ($2, $3::uuid)
                    GROUP BY d.id
                    ORDER BY d.created_at, d.id
                    LIMIT $4
                    """,
                    owner_id, after_created_at, after_id, limit + 1,
                )

        has_more = len(rows) > limit
        page_rows = rows[:limit]

        items = [
            Document(
                id=str(r["id"]), title=r["title"], body=r["body"],
                owner_id=r["owner_id"], tags=tuple(r["tags"]),
            )
            for r in page_rows
        ]

        next_cursor = None
        if has_more:
            last = page_rows[-1]
            next_cursor = _encode_cursor(last["created_at"], str(last["id"]))

        return Page(items=items, next_cursor=next_cursor)


async def _demo() -> None:
    pool = await create_pool()
    await apply_schema(pool)
    service = DocumentService(pool, cache_capacity=2)

    for i in range(5):
        await service.create_document(f"Doc {i}", f"body {i}", owner_id="user-1")

    print("\n--- Dedup demo ---")
    first = await service.create_document("Doc 0", "body 0", owner_id="user-1")
    duplicate = await service.create_document("Doc 0", "body 0", owner_id="user-1")
    print(f"Same id returned for identical content: {first.id == duplicate.id}")

    print("\n--- Pagination demo (page size 2) ---")
    page1 = await service.list_documents("user-1", limit=2)
    print(f"Page 1: {[d.title for d in page1.items]}  next_cursor={page1.next_cursor is not None}")
    page2 = await service.list_documents("user-1", limit=2, cursor=page1.next_cursor)
    print(f"Page 2: {[d.title for d in page2.items]}  next_cursor={page2.next_cursor is not None}")

    print("\n--- LRU cache demo (capacity=2) ---")
    await service.get_document(first.id)
    print(f"cache_info after warm access: {service.cache_info()}")

    await pool.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(_demo())
