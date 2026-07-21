"""
Tests for Build 01, Lesson 06.
Run with: pytest test_lesson.py -v

Runs against a real Postgres database — set CORTEX_DATABASE_URL if your
setup differs from the default.
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
    # Truncate on setup, not just teardown — guarantees a clean table
    # regardless of what ran before this test (a manual demo run, a
    # crashed previous session, etc). Relying only on teardown cleanup
    # is exactly the kind of assumption that works in CI and fails the
    # first time a human runs the demo locally before the tests.
    async with p.acquire() as conn:
        await conn.execute(
            "TRUNCATE document_tags, documents, tags, users RESTART IDENTITY CASCADE"
        )
    yield p
    await p.close()


@pytest.fixture
def service(pool):
    return DocumentService(pool)


# ── Dedup ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_identical_content_from_same_owner_dedups(service, pool):
    first = await service.create_document("Same", "content", owner_id="user-1")
    second = await service.create_document("Same", "content", owner_id="user-1")

    assert first.id == second.id

    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT count(*) FROM documents")
    assert count == 1


@pytest.mark.asyncio
async def test_identical_content_from_different_owners_does_not_dedup(service):
    first = await service.create_document("Same", "content", owner_id="user-1")
    second = await service.create_document("Same", "content", owner_id="user-2")

    assert first.id != second.id


@pytest.mark.asyncio
async def test_dedup_hit_keeps_original_tags_not_new_ones(service):
    original = await service.create_document(
        "Same", "content", owner_id="user-1", tags=["original"]
    )
    duplicate = await service.create_document(
        "Same", "content", owner_id="user-1", tags=["ignored"]
    )

    assert duplicate.id == original.id
    assert duplicate.tags == ("original",)


# ── Keyset pagination ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pagination_respects_limit_and_reports_next_cursor(service):
    for i in range(5):
        await service.create_document(f"Doc {i}", f"body {i}", owner_id="user-1")

    page = await service.list_documents("user-1", limit=2)

    assert len(page.items) == 2
    assert page.next_cursor is not None


@pytest.mark.asyncio
async def test_pagination_last_page_has_no_next_cursor(service):
    for i in range(3):
        await service.create_document(f"Doc {i}", f"body {i}", owner_id="user-1")

    page = await service.list_documents("user-1", limit=10)

    assert len(page.items) == 3
    assert page.next_cursor is None


@pytest.mark.asyncio
async def test_pagination_walks_every_document_exactly_once(service):
    created_ids = set()
    for i in range(7):
        doc = await service.create_document(f"Doc {i}", f"body {i}", owner_id="user-1")
        created_ids.add(doc.id)

    seen_ids: list[str] = []
    cursor = None
    while True:
        page = await service.list_documents("user-1", limit=3, cursor=cursor)
        seen_ids.extend(d.id for d in page.items)
        if page.next_cursor is None:
            break
        cursor = page.next_cursor

    # every document appears exactly once across all pages — no gaps,
    # no duplicates, which is the actual correctness bar for pagination
    assert sorted(seen_ids) == sorted(created_ids)
    assert len(seen_ids) == len(set(seen_ids))


# ── LRU cache ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_second_get_document_call_is_a_cache_hit(pool):
    service = DocumentService(pool)
    doc = await service.create_document("Cached", "body", owner_id="user-1")

    before = service.cache_info()
    await service.get_document(doc.id)
    after = service.cache_info()

    assert after["hits"] == before["hits"] + 1
    assert after["misses"] == before["misses"]


@pytest.mark.asyncio
async def test_lru_evicts_least_recently_used_beyond_capacity(pool):
    service = DocumentService(pool, cache_capacity=2)
    doc1 = await service.create_document("A", "a", owner_id="user-1")
    await service.create_document("B", "b", owner_id="user-1")
    await service.create_document("C", "c", owner_id="user-1")
    # capacity is 2, three documents created — doc1 should be evicted by now

    before = service.cache_info()
    await service.get_document(doc1.id)
    after = service.cache_info()

    assert after["misses"] == before["misses"] + 1
