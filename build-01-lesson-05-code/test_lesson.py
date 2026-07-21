"""
Tests for Build 01, Lesson 05.
Run with: pytest test_lesson.py -v

These run against a real Postgres database — set CORTEX_DATABASE_URL if your
setup differs from the default (postgresql://postgres:postgres@127.0.0.1:5432/cortex).
Each test truncates all tables afterward, so tests don't leak state into
each other even though they share one database.
"""

import os

import pytest
import pytest_asyncio

from lesson_code import DocumentService, apply_schema, create_pool

DSN = os.environ.get(
    "CORTEX_DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/cortex"
)


@pytest_asyncio.fixture
async def pool():
    p = await create_pool(DSN)
    await apply_schema(p)
    yield p
    async with p.acquire() as conn:
        await conn.execute(
            "TRUNCATE document_tags, documents, tags, users RESTART IDENTITY CASCADE"
        )
    await p.close()


@pytest.fixture
def service(pool):
    return DocumentService(pool)


@pytest.mark.asyncio
async def test_create_document_returns_a_document(service):
    doc = await service.create_document("Test Title", "Test body", owner_id="user-1")

    assert doc.title == "Test Title"
    assert doc.owner_id == "user-1"
    assert doc.tags == ()
    assert doc.id  # a real UUID came back from Postgres


@pytest.mark.asyncio
async def test_get_document_roundtrips_with_tags(service):
    created = await service.create_document(
        "Roundtrip", "body", owner_id="user-1", tags=["urgent", "draft"]
    )

    fetched = await service.get_document(created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert set(fetched.tags) == {"urgent", "draft"}


@pytest.mark.asyncio
async def test_get_document_missing_returns_none(service):
    # a syntactically valid UUID that simply doesn't exist
    result = await service.get_document("00000000-0000-0000-0000-000000000000")

    assert result is None


@pytest.mark.asyncio
async def test_get_document_with_malformed_id_returns_none_not_an_error(service):
    result = await service.get_document("not-a-uuid-at-all")

    assert result is None


@pytest.mark.asyncio
async def test_list_documents_isolates_by_owner(service):
    await service.create_document("Doc A", "body", owner_id="user-1")
    await service.create_document("Doc B", "body", owner_id="user-2")

    user_1_docs = await service.list_documents(owner_id="user-1")

    assert len(user_1_docs) == 1
    assert user_1_docs[0].title == "Doc A"


@pytest.mark.asyncio
async def test_shared_tags_deduplicate_to_one_row(service, pool):
    await service.create_document("Doc A", "body", owner_id="user-1", tags=["shared"])
    await service.create_document("Doc B", "body", owner_id="user-1", tags=["shared"])

    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT count(*) FROM tags WHERE name = 'shared'")

    # two documents, one tag row — this is the payoff of tags being a
    # separate table instead of a text column on documents.
    assert count == 1


@pytest.mark.asyncio
async def test_create_document_without_tags_returns_empty_tuple(service):
    doc = await service.create_document("No tags", "body", owner_id="user-1")

    assert doc.tags == ()
