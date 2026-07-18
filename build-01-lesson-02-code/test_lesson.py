"""
Tests for Build 01, Lesson 02.
Run with: pytest test_lesson.py -v

These verify the concept, not just the code: that the service layer is async,
that it correctly isolates documents by owner, and that the decorator doesn't
swallow return values or exceptions.
"""

import pytest

from lesson_code import Document, DocumentService, log_call


@pytest.mark.asyncio
async def test_create_document_returns_a_document():
    service = DocumentService()
    doc = await service.create_document("Test Title", "Test body", owner_id="user-1")

    assert isinstance(doc, Document)
    assert doc.title == "Test Title"
    assert doc.owner_id == "user-1"
    assert doc.id  # a UUID was generated


@pytest.mark.asyncio
async def test_get_document_roundtrips():
    service = DocumentService()
    created = await service.create_document("Roundtrip", "body", owner_id="user-1")

    fetched = await service.get_document(created.id)

    assert fetched == created


@pytest.mark.asyncio
async def test_get_document_missing_returns_none():
    service = DocumentService()

    result = await service.get_document("not-a-real-id")

    assert result is None


@pytest.mark.asyncio
async def test_list_documents_isolates_by_owner():
    service = DocumentService()
    await service.create_document("Doc A", "body", owner_id="user-1")
    await service.create_document("Doc B", "body", owner_id="user-2")

    user_1_docs = await service.list_documents(owner_id="user-1")

    assert len(user_1_docs) == 1
    assert user_1_docs[0].title == "Doc A"


@pytest.mark.asyncio
async def test_concurrent_creates_do_not_lose_writes():
    """This is the test that would fail if create_document weren't properly
    async-safe — a common bug once real concurrency shows up in Build 09."""
    service = DocumentService()

    import asyncio

    await asyncio.gather(
        *[
            service.create_document(f"Doc {i}", "body", owner_id="user-1")
            for i in range(20)
        ]
    )

    docs = await service.list_documents(owner_id="user-1")
    assert len(docs) == 20


@pytest.mark.asyncio
async def test_log_call_decorator_preserves_return_value():
    @log_call
    async def add(a: int, b: int) -> int:
        return a + b

    result = await add(2, 3)

    assert result == 5


@pytest.mark.asyncio
async def test_log_call_decorator_propagates_exceptions():
    @log_call
    async def always_fails() -> None:
        raise ValueError("expected failure")

    with pytest.raises(ValueError, match="expected failure"):
        await always_fails()
