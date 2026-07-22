"""
Tests for Build 02, Lesson 07 (Build Milestone).
Run with: pytest test_lesson.py -v

Runs against a real Postgres database (same as every Build 01/02 lesson
that touches storage). model.joblib must exist — run
`python train_classifier.py` first if it doesn't (setup.sh does this).
"""

import os
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from lesson_code import MODEL_PATH, apply_schema, create_app, create_pool

DSN = os.environ.get(
    "CORTEX_DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/cortex"
)

VALID_CATEGORIES = {"note", "report", "spec", "legal"}


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


def test_classify_endpoint_returns_a_valid_category_and_confidence(pool):
    with TestClient(create_app(data_dir=Path("/nonexistent"))) as client:
        response = client.post(
            "/classify", json={"title": "quick note", "body": "lunch at noon", "tags": []}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["category"] in VALID_CATEGORIES
    assert 0.0 <= body["confidence"] <= 1.0


def test_created_document_is_auto_tagged_with_a_category(pool):
    with TestClient(create_app(data_dir=Path("/nonexistent"))) as client:
        response = client.post(
            "/documents",
            json={"title": "Onboarding", "body": "Welcome to the team.", "owner_id": "user-1", "tags": []},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["category"] in VALID_CATEGORIES
    assert body["category_confidence"] is not None


def test_persisted_category_matches_what_get_returns(pool):
    with TestClient(create_app(data_dir=Path("/nonexistent"))) as client:
        created = client.post(
            "/documents",
            json={"title": "Report Draft", "body": "Q3 numbers are in.", "owner_id": "user-1", "tags": []},
        ).json()

        fetched = client.get(f"/documents/{created['id']}").json()

    assert fetched["category"] == created["category"]
    assert fetched["category_confidence"] == created["category_confidence"]


def test_auto_tagging_agrees_with_standalone_classify_for_the_same_input(pool):
    """The consistency check that actually matters: the category a
    document gets on upload and the category /classify returns for the
    identical title/body/tags should be the same — they're the same
    underlying function call, and this test would catch it if they ever
    drifted apart."""
    payload = {"title": "Design Review", "body": "Notes from today's review.", "tags": ["reviewed"]}

    with TestClient(create_app(data_dir=Path("/nonexistent"))) as client:
        standalone = client.post("/classify", json=payload).json()
        created = client.post(
            "/documents", json={**payload, "owner_id": "user-1"}
        ).json()

    assert created["category"] == standalone["category"]


def test_dedup_hit_preserves_original_category_not_reclassified(pool):
    with TestClient(create_app(data_dir=Path("/nonexistent"))) as client:
        first = client.post(
            "/documents", json={"title": "Same", "body": "content", "owner_id": "user-1", "tags": []}
        ).json()
        second = client.post(
            "/documents", json={"title": "Same", "body": "content", "owner_id": "user-1", "tags": []}
        ).json()

    assert first["id"] == second["id"]
    assert first["category"] == second["category"]
    assert first["category_confidence"] == second["category_confidence"]


def test_document_creation_succeeds_even_without_a_loaded_classifier(pool):
    """Verified degradation, not assumed: with no classifier available,
    document creation still succeeds — category is just None — rather
    than the whole request failing because one optional feature is down."""
    with TestClient(
        create_app(data_dir=Path("/nonexistent"), model_path=Path("/nonexistent/model.joblib"))
    ) as client:
        response = client.post(
            "/documents", json={"title": "t", "body": "b", "owner_id": "user-1", "tags": []}
        )

    assert response.status_code == 201
    assert response.json()["category"] is None


def test_classify_endpoint_fails_loud_without_a_loaded_classifier(pool):
    with TestClient(
        create_app(data_dir=Path("/nonexistent"), model_path=Path("/nonexistent/model.joblib"))
    ) as client:
        response = client.post("/classify", json={"title": "t", "body": "b", "tags": []})

    assert response.status_code == 503


def test_model_file_exists_after_training():
    assert MODEL_PATH.exists(), "run `python train_classifier.py` before the test suite"
