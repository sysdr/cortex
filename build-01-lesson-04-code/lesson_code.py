"""
Cortex — Build 01, Lesson 04
FastAPI: Cortex's /documents and /users endpoints.

This is the first lesson where two previous lessons meet: Lesson 02's async
service layer gets an HTTP face, and Lesson 03's seed.sh output becomes the
first thing you can curl out of a running Cortex. No Postgres yet — that's
Lesson 05. The in-memory store here is exactly the one from Lesson 02.
"""

from __future__ import annotations

import asyncio
import functools
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, TypeVar

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

T = TypeVar("T")


# ── Decorator, carried over unchanged from Lesson 02 ───────────────────────


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


@dataclass(frozen=True, slots=True)
class User:
    id: str
    email: str
    display_name: str


# ── Service layer — DocumentService gains one method this lesson ──────────


class DocumentService:
    def __init__(self) -> None:
        self._store: dict[str, Document] = {}
        self._lock = asyncio.Lock()

    @log_call
    async def create_document(self, title: str, body: str, owner_id: str) -> Document:
        doc = Document(id=str(uuid.uuid4()), title=title, body=body, owner_id=owner_id)
        async with self._lock:
            self._store[doc.id] = doc
        return doc

    @log_call
    async def get_document(self, document_id: str) -> Document | None:
        return self._store.get(document_id)

    @log_call
    async def list_documents(self, owner_id: str) -> list[Document]:
        return [d for d in self._store.values() if d.owner_id == owner_id]

    @log_call
    async def load_seeded(self, dir_path: Path) -> int:
        """Bulk-load pre-made Document records — e.g. from Lesson 03's
        seed.sh — directly into the store, skipping any that already
        exist. Plain synchronous file IO is fine for a handful of startup
        files; it stops being fine once this reads from Postgres in
        Lesson 05, which is why the method boundary exists at all."""
        loaded = 0
        async with self._lock:
            for file in sorted(dir_path.glob("*.json")):
                data = json.loads(file.read_text())
                if data["id"] in self._store:
                    continue
                self._store[data["id"]] = Document(**data)
                loaded += 1
        return loaded


class UserService:
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


# ── API schemas — the HTTP contract, separate from the domain models ──────
# AI relevance: this separation matters more once Build 04 has an LLM
# calling these endpoints via function calling — the schema is the contract
# a model reasons about, and it can evolve independently of internal storage.


class DocumentCreate(BaseModel):
    title: str
    body: str
    owner_id: str


class DocumentOut(BaseModel):
    id: str
    title: str
    body: str
    owner_id: str


class UserCreate(BaseModel):
    email: str
    display_name: str


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str


# ── App factory — lets tests build an isolated app per test ───────────────


def create_app(data_dir: Path | None = None) -> FastAPI:
    document_service = DocumentService()
    user_service = UserService()
    resolved_dir = data_dir or Path(os.environ.get("CORTEX_DATA_DIR", "./data/documents"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if resolved_dir.exists():
            count = await document_service.load_seeded(resolved_dir)
            print(f"Loaded {count} seeded documents from {resolved_dir}")
        yield

    app = FastAPI(title="Cortex", lifespan=lifespan)

    def get_document_service() -> DocumentService:
        return document_service

    def get_user_service() -> UserService:
        return user_service

    @app.post("/documents", response_model=DocumentOut, status_code=201)
    async def create_document_endpoint(
        payload: DocumentCreate,
        service: DocumentService = Depends(get_document_service),
    ) -> Document:
        return await service.create_document(payload.title, payload.body, payload.owner_id)

    @app.get("/documents/{document_id}", response_model=DocumentOut)
    async def get_document_endpoint(
        document_id: str,
        service: DocumentService = Depends(get_document_service),
    ) -> Document:
        doc = await service.get_document(document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return doc

    @app.get("/documents", response_model=list[DocumentOut])
    async def list_documents_endpoint(
        owner_id: str,
        service: DocumentService = Depends(get_document_service),
    ) -> list[Document]:
        return await service.list_documents(owner_id)

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


# Default app instance — this is what `uvicorn lesson_code:app` serves.
app = create_app()
