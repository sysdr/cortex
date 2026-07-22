"""
Cortex — Build 02, Lesson 07 (Build Milestone)
/classify endpoint: every document uploaded to Cortex gets auto-tagged by
a model you trained.

This is where two builds meet. DocumentService below is Build 01's exact
service — dedup, keyset pagination, LRU cache, all unchanged — with one
addition: create_document now calls the classifier trained in
train_classifier.py and stores its prediction on the row. A standalone
POST /classify endpoint exposes the same classification logic without
requiring a document to actually be created, for testing and for any
future caller (an agent, in Build 07) that just wants a prediction.
"""

from __future__ import annotations

import functools
import hashlib
import os
import time
import warnings
from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections import OrderedDict
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, TypeVar

import asyncpg
import joblib
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel

T = TypeVar("T")

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
MODEL_PATH = Path(__file__).parent / "model.joblib"
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
    category: str | None = None
    category_confidence: float | None = None


@dataclass(frozen=True, slots=True)
class Page:
    items: list[Document]
    next_cursor: str | None


# ── The classifier — trained in train_classifier.py, loaded once here ──


def extract_features(title: str, body: str, tags: list[str]) -> pd.DataFrame:
    """The exact same three features Lesson 04 trained on: body length,
    word count, tag count. This function is the seam between "arbitrary
    text a user typed" and "the numeric input the model actually expects"
    — every future retrain has to keep this function's output shape
    stable, or the model and the feature extractor drift out of sync."""
    return pd.DataFrame(
        [{"body_length": len(body), "word_count": len(body.split()), "num_tags": len(tags)}]
    )


def classify(pipeline, title: str, body: str, tags: list[str]) -> tuple[str, float]:
    features = extract_features(title, body, tags)
    category = pipeline.predict(features)[0]
    proba = pipeline.predict_proba(features)[0]
    confidence = float(proba.max())
    return category, confidence


def _load_classifier(path: Path):
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="Setting the shape on a NumPy array has been deprecated",
            category=DeprecationWarning,
        )
        return joblib.load(path)


# ── LRU cache, unchanged from Build 01 ─────────────────────────────────


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


class DocumentService:
    """Build 01's exact service, with one addition: create_document now
    classifies new (non-duplicate) documents and stores the prediction.
    A dedup hit returns the ORIGINAL document's category, the same way it
    already returns the original's tags — reclassifying a duplicate would
    make classification results depend on submission order, which isn't
    a property a real system should have."""

    def __init__(self, pool: asyncpg.Pool, classifier=None, cache_capacity: int = 100) -> None:
        self._pool = pool
        self._classifier = classifier
        self._cache = LRUCache(cache_capacity)

    def cache_info(self) -> dict[str, int]:
        return {"hits": self._cache.hits, "misses": self._cache.misses, "size": len(self._cache._store)}

    @log_call
    async def create_document(
        self, title: str, body: str, owner_id: str, tags: list[str] | None = None
    ) -> Document:
        tags = tags or []
        content_hash = hashlib.sha256(f"{title}\n{body}".encode()).hexdigest()

        async with self._pool.acquire() as conn, conn.transaction():
            existing = await conn.fetchrow(
                "SELECT id FROM documents WHERE owner_id = $1 AND content_hash = $2",
                owner_id, content_hash,
            )

            if existing is None:
                category, confidence = (None, None)
                if self._classifier is not None:
                    category, confidence = classify(self._classifier, title, body, tags)

                row = await conn.fetchrow(
                    """
                    INSERT INTO documents (title, body, owner_id, content_hash, category, category_confidence)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id, title, body, owner_id, category, category_confidence
                    """,
                    title, body, owner_id, content_hash, category, confidence,
                )
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
                        "INSERT INTO document_tags (document_id, tag_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                        row["id"], tag_id,
                    )
                final_tags: tuple[str, ...] = tuple(tags)
            else:
                row = await conn.fetchrow(
                    "SELECT id, title, body, owner_id, category, category_confidence FROM documents WHERE id = $1",
                    existing["id"],
                )
                tag_rows = await conn.fetch(
                    "SELECT t.name FROM tags t JOIN document_tags dt ON dt.tag_id = t.id WHERE dt.document_id = $1",
                    row["id"],
                )
                final_tags = tuple(r["name"] for r in tag_rows)

        doc = Document(
            id=str(row["id"]), title=row["title"], body=row["body"], owner_id=row["owner_id"],
            tags=final_tags, category=row["category"], category_confidence=row["category_confidence"],
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
                    SELECT d.id, d.title, d.body, d.owner_id, d.category, d.category_confidence,
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
            id=str(row["id"]), title=row["title"], body=row["body"], owner_id=row["owner_id"],
            tags=tuple(row["tags"]), category=row["category"], category_confidence=row["category_confidence"],
        )
        self._cache.put(doc.id, doc)
        return doc

    @log_call
    async def list_documents(self, owner_id: str, *, limit: int = 20, cursor: str | None = None) -> Page:
        after_created_at: datetime | None = None
        after_id: str | None = None
        if cursor is not None:
            after_created_at, after_id = _decode_cursor(cursor)

        base_select = """
            SELECT d.id, d.title, d.body, d.owner_id, d.created_at, d.category, d.category_confidence,
                   COALESCE(array_agg(t.name) FILTER (WHERE t.name IS NOT NULL), '{}') AS tags
            FROM documents d
            LEFT JOIN document_tags dt ON dt.document_id = d.id
            LEFT JOIN tags t ON t.id = dt.tag_id
        """

        async with self._pool.acquire() as conn:
            if cursor is None:
                rows = await conn.fetch(
                    base_select + " WHERE d.owner_id = $1 GROUP BY d.id ORDER BY d.created_at, d.id LIMIT $2",
                    owner_id, limit + 1,
                )
            else:
                rows = await conn.fetch(
                    base_select + """
                    WHERE d.owner_id = $1 AND (d.created_at, d.id) > ($2, $3::uuid)
                    GROUP BY d.id ORDER BY d.created_at, d.id LIMIT $4
                    """,
                    owner_id, after_created_at, after_id, limit + 1,
                )

        has_more = len(rows) > limit
        page_rows = rows[:limit]
        items = [
            Document(
                id=str(r["id"]), title=r["title"], body=r["body"], owner_id=r["owner_id"],
                tags=tuple(r["tags"]), category=r["category"], category_confidence=r["category_confidence"],
            )
            for r in page_rows
        ]
        next_cursor = None
        if has_more:
            last = page_rows[-1]
            next_cursor = _encode_cursor(last["created_at"], str(last["id"]))
        return Page(items=items, next_cursor=next_cursor)


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
    category: str | None
    category_confidence: float | None


class DocumentPageOut(BaseModel):
    items: list[DocumentOut]
    next_cursor: str | None


class ClassifyRequest(BaseModel):
    title: str
    body: str
    tags: list[str] = []


class ClassifyResponse(BaseModel):
    category: str
    confidence: float


def _to_document_out(doc: Document) -> DocumentOut:
    return DocumentOut(
        id=doc.id, title=doc.title, body=doc.body, owner_id=doc.owner_id, tags=list(doc.tags),
        category=doc.category, category_confidence=doc.category_confidence,
    )


# ── App factory ─────────────────────────────────────────────────────────


def create_app(data_dir: Path | None = None, model_path: Path | None = None) -> FastAPI:
    resolved_data_dir = data_dir or Path(os.environ.get("CORTEX_DATA_DIR", "./data/documents"))
    resolved_model_path = model_path or MODEL_PATH
    state: dict[str, object] = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        real_pool = await create_pool()
        await apply_schema(real_pool)

        classifier = _load_classifier(resolved_model_path) if resolved_model_path.exists() else None

        document_service = DocumentService(real_pool, classifier=classifier)
        state["document_service"] = document_service
        state["classifier"] = classifier

        yield
        await real_pool.close()

    app = FastAPI(title="Cortex", lifespan=lifespan)

    def get_document_service() -> DocumentService:
        return state["document_service"]  # type: ignore[return-value]

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/documents", response_model=DocumentOut, status_code=201)
    async def create_document_endpoint(
        payload: DocumentCreate, service: DocumentService = Depends(get_document_service)
    ) -> DocumentOut:
        doc = await service.create_document(payload.title, payload.body, payload.owner_id, payload.tags)
        return _to_document_out(doc)

    @app.get("/documents/{document_id}", response_model=DocumentOut)
    async def get_document_endpoint(
        document_id: str, service: DocumentService = Depends(get_document_service)
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
        page = await service.list_documents(owner_id, limit=limit, cursor=cursor)
        return DocumentPageOut(items=[_to_document_out(d) for d in page.items], next_cursor=page.next_cursor)

    @app.post("/classify", response_model=ClassifyResponse)
    async def classify_endpoint(payload: ClassifyRequest) -> ClassifyResponse:
        """Standalone classification — doesn't create or touch a document.
        Exists for testing the classifier in isolation, and for any future
        caller (an agent, in Build 07) that just wants a prediction."""
        classifier = state.get("classifier")
        if classifier is None:
            raise HTTPException(status_code=503, detail="Classifier not loaded")
        category, confidence = classify(classifier, payload.title, payload.body, payload.tags)
        return ClassifyResponse(category=category, confidence=confidence)

    return app


app = create_app()
