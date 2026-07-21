"""
Tests for Build 01, Lesson 04.
Run with: pytest test_lesson.py -v

Each test builds its own isolated app via create_app(), so no test leaks
state into another — the same discipline the service layer itself uses.
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from lesson_code import create_app


def test_create_document_returns_201_and_the_document():
    client = TestClient(create_app())

    response = client.post(
        "/documents", json={"title": "Test Doc", "body": "body text", "owner_id": "user-1"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Test Doc"
    assert body["owner_id"] == "user-1"
    assert "id" in body


def test_get_document_roundtrips():
    client = TestClient(create_app())
    created = client.post(
        "/documents", json={"title": "Roundtrip", "body": "b", "owner_id": "user-1"}
    ).json()

    response = client.get(f"/documents/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_document_missing_returns_404():
    client = TestClient(create_app())

    response = client.get("/documents/not-a-real-id")

    assert response.status_code == 404


def test_list_documents_filters_by_owner():
    client = TestClient(create_app())
    client.post("/documents", json={"title": "A", "body": "b", "owner_id": "user-1"})
    client.post("/documents", json={"title": "B", "body": "b", "owner_id": "user-2"})

    response = client.get("/documents", params={"owner_id": "user-1"})

    assert response.status_code == 200
    docs = response.json()
    assert len(docs) == 1
    assert docs[0]["title"] == "A"


def test_create_user_and_get_it_back():
    client = TestClient(create_app())

    created = client.post(
        "/users", json={"email": "a@example.com", "display_name": "Ada"}
    ).json()
    response = client.get(f"/users/{created['id']}")

    assert response.status_code == 200
    assert response.json()["email"] == "a@example.com"


def test_get_user_missing_returns_404():
    client = TestClient(create_app())

    response = client.get("/users/not-a-real-id")

    assert response.status_code == 404


def test_startup_loads_seeded_documents_from_disk(tmp_path: Path):
    seed_dir = tmp_path / "documents"
    seed_dir.mkdir()
    (seed_dir / "doc-001.json").write_text(
        json.dumps({"id": "doc-001", "title": "Seeded", "body": "b", "owner_id": "user-1"})
    )

    # TestClient as a context manager triggers the lifespan (startup) event
    with TestClient(create_app(data_dir=seed_dir)) as client:
        response = client.get("/documents/doc-001")

    assert response.status_code == 200
    assert response.json()["title"] == "Seeded"


def test_startup_with_no_data_dir_does_not_error(tmp_path: Path):
    missing_dir = tmp_path / "does-not-exist"

    with TestClient(create_app(data_dir=missing_dir)) as client:
        response = client.get("/documents", params={"owner_id": "anyone"})

    assert response.status_code == 200
    assert response.json() == []
