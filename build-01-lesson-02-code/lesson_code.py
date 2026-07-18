"""
Cortex — Build 01, Lesson 02
Python async, decorators & type hints — Cortex's service layer.

This module is intentionally storage-agnostic: no Postgres yet (that's Lesson 05),
no FastAPI yet (that's Lesson 04). It's the shape every future service in Cortex
will follow, proven out against an in-memory store first.
"""

from __future__ import annotations

import asyncio
import functools
import time
import uuid
from dataclasses import dataclass, field
from typing import Awaitable, Callable, TypeVar

# ── Type hints: making the service's contract machine-checkable ─────────────
# AI relevance: every service Cortex adds later (classifier, RAG, agent) will
# be called by other services and, eventually, by an LLM via function calling.
# A precise contract here is what makes that safe.

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Document:
    """A single document in Cortex. Immutable once created — mutations create
    a new version, not an in-place edit. This matters later: Build 09's
    caching layer assumes documents are safe to hash and compare by value."""

    id: str
    title: str
    body: str
    owner_id: str


# ── Decorators: cross-cutting behavior without touching business logic ─────
# AI relevance: this exact pattern — wrap, time, log, return — is what Build 09
# uses to trace every LLM call. Learning it on a boring in-memory store now
# means Build 09 is a rename, not a new concept.


def log_call(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """Async decorator: logs method name, duration, and outcome of every
    service call. A stand-in today for what will become real observability
    (Langfuse/LangSmith tracing) once Cortex starts calling LLMs."""

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


# ── The service layer: async by default, storage swappable later ──────────
# AI relevance: async matters here for the same reason it'll matter for the
# LLM client in Build 04 — a document upload, a classifier call, and a chat
# request all need to happen concurrently without blocking each other.


class DocumentService:
    """In-memory document store. The public method signatures on this class
    won't change when Lesson 05 swaps the backing store for Postgres — that's
    the point of a service layer: callers depend on behavior, not storage."""

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


# ── Demo: run this file directly to see the service layer in action ───────


async def _demo() -> None:
    service = DocumentService()

    # Concurrent creates — this is the part a synchronous version couldn't do
    # without blocking each request on the previous one finishing.
    created = await asyncio.gather(
        service.create_document("Q3 Roadmap", "...", owner_id="user-1"),
        service.create_document("Onboarding Notes", "...", owner_id="user-1"),
        service.create_document("Design Review", "...", owner_id="user-2"),
    )

    docs_for_user_1 = await service.list_documents(owner_id="user-1")
    print(f"\nuser-1 has {len(docs_for_user_1)} documents:")
    for d in docs_for_user_1:
        print(f"  - {d.title} ({d.id[:8]}...)")

    missing = await service.get_document("does-not-exist")
    print(f"\nLooking up a missing document returns: {missing}")


if __name__ == "__main__":
    asyncio.run(_demo())
