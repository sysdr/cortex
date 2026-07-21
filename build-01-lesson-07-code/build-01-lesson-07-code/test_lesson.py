"""
Tests for Build 01, Lesson 07.
Run with: pytest test_lesson.py -v

Runs against a real Postgres database (same as Lessons 05-06) — this is the
application code that also runs inside the Docker container, so testing it
directly here is testing exactly what docker-compose.yml will run.
"""

import json
import os
from pathlib import Path

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


def test_health_endpoint(pool):
    with TestClient(create_app(data_dir=Path("/nonexistent"))) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_get_document_roundtrip(pool):
    with TestClient(create_app(data_dir=Path("/nonexistent"))) as client:
        created = client.post(
            "/documents",
            json={"title": "Test", "body": "body", "owner_id": "user-1", "tags": ["a"]},
        ).json()

        response = client.get(f"/documents/{created['id']}")

    assert response.status_code == 200
    assert response.json()["tags"] == ["a"]


def test_get_document_missing_returns_404(pool):
    with TestClient(create_app(data_dir=Path("/nonexistent"))) as client:
        response = client.get("/documents/not-a-real-id")

    assert response.status_code == 404


def test_create_document_dedups_via_endpoint(pool):
    with TestClient(create_app(data_dir=Path("/nonexistent"))) as client:
        first = client.post(
            "/documents", json={"title": "Dup", "body": "same", "owner_id": "user-1"}
        ).json()
        second = client.post(
            "/documents", json={"title": "Dup", "body": "same", "owner_id": "user-1"}
        ).json()

    assert first["id"] == second["id"]


def test_list_documents_pagination_via_endpoint(pool):
    with TestClient(create_app(data_dir=Path("/nonexistent"))) as client:
        for i in range(5):
            client.post(
                "/documents",
                json={"title": f"Doc {i}", "body": f"b{i}", "owner_id": "user-1"},
            )

        page1 = client.get("/documents", params={"owner_id": "user-1", "limit": 2}).json()
        page2 = client.get(
            "/documents",
            params={"owner_id": "user-1", "limit": 2, "cursor": page1["next_cursor"]},
        ).json()

    assert len(page1["items"]) == 2
    assert page1["next_cursor"] is not None
    assert len(page2["items"]) == 2
    # no overlap between pages
    page1_ids = {d["id"] for d in page1["items"]}
    page2_ids = {d["id"] for d in page2["items"]}
    assert page1_ids.isdisjoint(page2_ids)


def test_users_endpoints_roundtrip(pool):
    with TestClient(create_app(data_dir=Path("/nonexistent"))) as client:
        created = client.post(
            "/users", json={"email": "a@example.com", "display_name": "Ada"}
        ).json()
        response = client.get(f"/users/{created['id']}")

    assert response.status_code == 200
    assert response.json()["email"] == "a@example.com"


def test_seed_loading_via_lifespan(pool, tmp_path: Path):
    seed_dir = tmp_path / "documents"
    seed_dir.mkdir()
    (seed_dir / "doc-001.json").write_text(
        json.dumps({"id": "doc-001", "title": "Seeded", "body": "b", "owner_id": "user-1"})
    )

    with TestClient(create_app(data_dir=seed_dir)) as client:
        response = client.get("/documents", params={"owner_id": "user-1"})

    assert response.status_code == 200
    titles = [d["title"] for d in response.json()["items"]]
    assert "Seeded" in titles


def test_seed_loading_is_idempotent_across_restarts(pool, tmp_path: Path):
    """This is the test that matters for Docker specifically: a container
    restart re-runs the lifespan, and re-seeding shouldn't duplicate data.
    Lesson 06's dedup logic is what makes this true for free — seeding
    goes through create_document, not a raw insert."""
    seed_dir = tmp_path / "documents"
    seed_dir.mkdir()
    (seed_dir / "doc-001.json").write_text(
        json.dumps({"id": "doc-001", "title": "Seeded", "body": "b", "owner_id": "user-1"})
    )

    # First "container start"
    with TestClient(create_app(data_dir=seed_dir)):
        pass

    # Second "container start" — simulating a restart
    with TestClient(create_app(data_dir=seed_dir)) as client:
        response = client.get("/documents", params={"owner_id": "user-1"})

    assert len(response.json()["items"]) == 1  # not 2
