"""
Cortex — Build 01, Lesson 07
Docker & Docker Compose: Cortex API + Postgres, one `docker compose up`.

Two things converge in this lesson. First: Lesson 06 flagged that
list_documents' return type change (list[Document] -> Page) would need a
matching update to Lesson 04's FastAPI endpoint — this is that update,
applied deliberately, not silently. Second: everything that's been set up
by hand since Lesson 05 (install Postgres, create a database, set a
password) becomes something docker-compose.yml does for you.
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import json
import os
import time
import uuid
from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections import OrderedDict
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, TypeVar

import asyncpg
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel

T = TypeVar("T")

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
DEFAULT_DSN = "postgresql://postgres:postgres@127.0.0.1:5432/cortex"


def log_call(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
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


# ── Domain models ────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    title: str
    body: str
    owner_id: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Page:
    items: list[Document]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class User:
    id: str
    email: str
    display_name: str


# ── LRU cache — unchanged from Lesson 06 ───────────────────────────────


class LRUCache:
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
            self._store.popitem(last=False)


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


# ── DocumentService — Postgres, dedup, keyset pagination, LRU cache ──────
# Unchanged from Lesson 06. This is the entire point of the last six
# lessons' discipline: the service that finally gets an HTTP face today
# didn't have to change to get one.


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
        self, title: str, body: str, owner_id: str, tags: list[str] | None = None
    ) -> Document:
        tags = tags or []
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
                    owner_id, limit + 1,
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


class UserService:
    """Still in-memory, unlike DocumentService. Migrating users to Postgres
    the way documents were migrated in Lesson 05 is a straightforward,
    deliberately left-out exercise — not because it's hard, but because a
    lesson that migrates two services at once teaches neither move clearly."""

    def __init__(self) -> None:
        self._store: dict[str, User] = {}
        self._lock = asyncio.Lock()

    @log_call
    async def create_user(self, email: str, display_name: str) -> User:
        user = User(id=str(uuid.uuid4()), email=email, display_name=display_name)
        async with self._lock:
            self._store[user.id] = user
        return user

    @log_call
    async def get_user(self, user_id: str) -> User | None:
        return self._store.get(user_id)


async def load_seeded(service: DocumentService, dir_path: Path) -> int:
    """Loads seed.sh's JSON output through create_document, not a direct
    insert — which means Lesson 06's dedup logic makes this idempotent for
    free. Restarting the container doesn't create duplicate seed data;
    create_document simply recognizes it's seen this content before."""
    if not dir_path.exists():
        return 0
    loaded = 0
    for file in sorted(dir_path.glob("*.json")):
        data = json.loads(file.read_text())
        await service.create_document(
            data["title"], data["body"], data["owner_id"]
        )
        loaded += 1
    return loaded


# ── API schemas ─────────────────────────────────────────────────────────


class DocumentCreate(BaseModel):
    title: str
    body: str
    owner_id: str
    tags: list[str] = []


class DocumentOut(BaseModel):
    id: str
    title: str
    body: str
    owner_id: str
    tags: list[str]


class DocumentPageOut(BaseModel):
    items: list[DocumentOut]
    next_cursor: str | None


class UserCreate(BaseModel):
    email: str
    display_name: str


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str


def _to_document_out(doc: Document) -> DocumentOut:
    return DocumentOut(id=doc.id, title=doc.title, body=doc.body,
                         owner_id=doc.owner_id, tags=list(doc.tags))


# ── App factory ─────────────────────────────────────────────────────────


def create_app(data_dir: Path | None = None) -> FastAPI:
    """Deliberately does NOT accept an externally-created pool. A pool is
    bound to the event loop it was created on — handing one in from outside
    (e.g. from a pytest-asyncio fixture's loop) breaks the moment this app
    runs inside a different loop, which is exactly what happens under
    Starlette's TestClient. The app always creates and owns its pool, which
    also happens to be exactly how the real container runs."""
    resolved_data_dir = data_dir or Path(
        os.environ.get("CORTEX_DATA_DIR", "./data/documents")
    )
    state: dict[str, object] = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        real_pool = await create_pool()
        await apply_schema(real_pool)
        document_service = DocumentService(real_pool)
        user_service = UserService()
        state["document_service"] = document_service
        state["user_service"] = user_service

        loaded = await load_seeded(document_service, resolved_data_dir)
        print(f"Loaded/verified {loaded} seeded documents from {resolved_data_dir}")

        yield

        await real_pool.close()

    app = FastAPI(title="Cortex", lifespan=lifespan)

    def get_document_service() -> DocumentService:
        return state["document_service"]  # type: ignore[return-value]

    def get_user_service() -> UserService:
        return state["user_service"]  # type: ignore[return-value]

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/documents", response_model=DocumentOut, status_code=201)
    async def create_document_endpoint(
        payload: DocumentCreate,
        service: DocumentService = Depends(get_document_service),
    ) -> DocumentOut:
        doc = await service.create_document(
            payload.title, payload.body, payload.owner_id, payload.tags
        )
        return _to_document_out(doc)

    @app.get("/documents/{document_id}", response_model=DocumentOut)
    async def get_document_endpoint(
        document_id: str,
        service: DocumentService = Depends(get_document_service),
    ) -> DocumentOut:
        doc = await service.get_document(document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return _to_document_out(doc)

    @app.get("/documents", response_model=DocumentPageOut)
    async def list_documents_endpoint(
        owner_id: str,
        limit: int = Query(default=20, ge=1, le=100),
        cursor: str | None = None,
        service: DocumentService = Depends(get_document_service),
    ) -> DocumentPageOut:
        # This endpoint is the payoff of Lesson 06's flagged breaking
        # change: limit/cursor query params and a Page-shaped response,
        # applied deliberately instead of quietly left mismatched.
        page = await service.list_documents(owner_id, limit=limit, cursor=cursor)
        return DocumentPageOut(
            items=[_to_document_out(d) for d in page.items],
            next_cursor=page.next_cursor,
        )

    @app.post("/users", response_model=UserOut, status_code=201)
    async def create_user_endpoint(
        payload: UserCreate,
        service: UserService = Depends(get_user_service),
    ) -> User:
        return await service.create_user(payload.email, payload.display_name)

    @app.get("/users/{user_id}", response_model=UserOut)
    async def get_user_endpoint(
        user_id: str,
        service: UserService = Depends(get_user_service),
    ) -> User:
        user = await service.get_user(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    return app


app = create_app()
