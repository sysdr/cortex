"""
Cortex — Build 01, Lesson 08 (Build Milestone)
Smoke test: does the whole thing actually work for someone who just cloned it?

This isn't a new set of unit tests for a new feature — Lessons 02 through 07
already have those, and they still pass unmodified. This is one continuous
walkthrough exercising every capability shipped since Lesson 04, in the
order a real user would actually hit them, against the real application
(same file the Docker container runs).

Run with: pytest test_lesson.py -v
"""

import os

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from lesson_code import apply_schema, create_app, create_pool

DSN = os.environ.get(
    "CORTEX_DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/cortex"
)


@pytest_asyncio.fixture
async def pool():
    p = await create_pool(DSN)
    await apply_schema(p)
    async with p.acquire() as conn:
        await conn.execute(
            "TRUNCATE document_tags, documents, tags, users RESTART IDENTITY CASCADE"
        )
    yield p
    await p.close()


def test_full_build_01_happy_path(pool):
    """One continuous story: sign up, create documents, tag them, hit
    dedup, page through a real result set, and confirm a 404 looks like a
    404. Every step here is a capability from a specific earlier lesson —
    called out inline — proven working together, not in isolation."""

    with TestClient(create_app()) as client:

        # --- Lesson 04: health check exists, service is up ---
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        # --- Lesson 04: users ---
        user = client.post(
            "/users", json={"email": "reader@example.com", "display_name": "New Reader"}
        )
        assert user.status_code == 201
        user_id = user.json()["id"]

        fetched_user = client.get(f"/users/{user_id}")
        assert fetched_user.status_code == 200
        assert fetched_user.json()["email"] == "reader@example.com"

        # --- Lesson 04 + 05: documents, now with real ownership + tags ---
        doc = client.post(
            "/documents",
            json={
                "title": "Getting Started with Cortex",
                "body": "This is the first document I ever created.",
                "owner_id": user_id,
                "tags": ["welcome", "first-doc"],
            },
        )
        assert doc.status_code == 201
        assert set(doc.json()["tags"]) == {"welcome", "first-doc"}
        doc_id = doc.json()["id"]

        # --- Lesson 04: 404 means 404, not an empty 200 ---
        missing = client.get("/documents/00000000-0000-0000-0000-000000000000")
        assert missing.status_code == 404

        # --- Lesson 06: dedup — re-submitting identical content returns
        # the same document instead of creating a duplicate ---
        duplicate = client.post(
            "/documents",
            json={
                "title": "Getting Started with Cortex",
                "body": "This is the first document I ever created.",
                "owner_id": user_id,
                "tags": ["ignored-on-dedup-hit"],
            },
        )
        assert duplicate.status_code == 201
        assert duplicate.json()["id"] == doc_id
        assert set(duplicate.json()["tags"]) == {"welcome", "first-doc"}  # not overwritten

        # --- Lesson 06: keyset pagination — walk a real multi-page result
        # set and confirm no gaps, no duplicates ---
        for i in range(6):
            client.post(
                "/documents",
                json={
                    "title": f"Note {i}",
                    "body": f"content {i}",
                    "owner_id": user_id,
                },
            )

        seen_ids: set[str] = set()
        cursor = None
        pages_walked = 0
        while True:
            params = {"owner_id": user_id, "limit": 3}
            if cursor:
                params["cursor"] = cursor
            page = client.get("/documents", params=params).json()
            seen_ids.update(d["id"] for d in page["items"])
            pages_walked += 1
            if page["next_cursor"] is None:
                break
            cursor = page["next_cursor"]
            assert pages_walked < 20  # guard against an infinite loop bug

        # 1 original doc + 6 new notes = 7 total, each seen exactly once
        assert len(seen_ids) == 7
        assert doc_id in seen_ids

        # --- Lesson 06: LRU cache — a second fetch of the same document
        # should be materially faster / a cache hit, verified indirectly
        # by confirming the data is still correct on repeat access ---
        first_fetch = client.get(f"/documents/{doc_id}")
        second_fetch = client.get(f"/documents/{doc_id}")
        assert first_fetch.json() == second_fetch.json()


def test_fresh_clone_starts_with_empty_state_before_seeding(pool):
    """Without seed.sh having run, a fresh clone's Cortex should be
    genuinely empty for a new owner — not pre-populated with anything
    left over from a previous run or a different lesson."""
    with TestClient(create_app()) as client:
        response = client.get("/documents", params={"owner_id": "someone-new"})

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_seed_data_is_reachable_once_seed_sh_has_run(pool, tmp_path):
    import json

    seed_dir = tmp_path / "documents"
    seed_dir.mkdir()
    (seed_dir / "doc-001.json").write_text(
        json.dumps(
            {"id": "doc-001", "title": "Q3 Roadmap", "body": "...", "owner_id": "user-1"}
        )
    )

    with TestClient(create_app(data_dir=seed_dir)) as client:
        response = client.get("/documents", params={"owner_id": "user-1"})

    titles = [d["title"] for d in response.json()["items"]]
    assert "Q3 Roadmap" in titles
