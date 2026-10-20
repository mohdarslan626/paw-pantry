from unittest.mock import patch

from sqlalchemy.exc import IntegrityError

from tests.conftest import admin_headers


def test_list_categories_returns_empty_list(client):
    response = client.get("/api/v1/categories/")

    assert response.status_code == 200
    assert response.json() == []


def test_create_category_returns_created_response(client, admin_headers):
    payload = {
        "name": "Dry Dog Food",
        "slug": "dry-dog-food",
        "description": "Complete dry food for dogs",
        "parent_id": None,
    }

    response = client.post("/api/v1/categories/", json=payload, headers=admin_headers)

    assert response.status_code == 201

    data = response.json()
    assert data["name"] == payload["name"]
    assert data["slug"] == payload["slug"]
    assert data["description"] == payload["description"]
    assert isinstance(data["id"], int)
    assert "created_at" in data


def test_create_category_rejects_invalid_slug(client, admin_headers):
    payload = {
        "name": "Invalid Slug Category",
        "slug": "Invalid Slug!",
        "description": None,
        "parent_id": None,
    }

    response = client.post("/api/v1/categories/", json=payload, headers=admin_headers)

    assert response.status_code == 422


def test_create_category_rejects_duplicate_slug(client, admin_headers):
    payload = {
        "name": "Dry Dog Food",
        "slug": "dry-dog-food",
        "description": None,
        "parent_id": None,
    }

    first_response = client.post("/api/v1/categories/", json=payload, headers=admin_headers)
    second_response = client.post("/api/v1/categories/", json=payload, headers=admin_headers)

    assert first_response.status_code == 201
    assert second_response.status_code in (400, 409)


def test_create_category_rejects_nonexistent_parent(client, admin_headers):
    payload = {
        "name": "Premium Dog Food",
        "slug": "premium-dog-food",
        "description": None,
        "parent_id": 999999999,
    }

    response = client.post("/api/v1/categories/", json=payload, headers=admin_headers)

    assert response.status_code in (400, 422)


def test_create_child_category_with_valid_parent(client, admin_headers):
    parent_payload = {
        "name": "Dog Food",
        "slug": "dog-food",
        "description": "Food for dogs",
        "parent_id": None,
    }

    parent_response = client.post("/api/v1/categories/", json=parent_payload, headers=admin_headers)
    assert parent_response.status_code == 201
    parent_id = parent_response.json()["id"]

    child_payload = {
        "name": "Dry Food",
        "slug": "dry-food",
        "description": "Dry food for dogs",
        "parent_id": parent_id,
    }

    child_response = client.post("/api/v1/categories/", json=child_payload, headers=admin_headers)

    assert child_response.status_code == 201
    assert child_response.json()["parent_id"] == parent_id
    assert child_response.json()["name"] == "Dry Food"


def test_create_category_rejects_name_that_is_too_short(client, admin_headers):
    payload = {
        "name": "A",
        "slug": "short-name",
        "description": None,
        "parent_id": None,
    }

    response = client.post("/api/v1/categories/", json=payload, headers=admin_headers)

    assert response.status_code == 422


def test_create_category_rejects_missing_name(client, admin_headers):
    payload = {
        "slug": "missing-name",
        "description": None,
        "parent_id": None,
    }

    response = client.post("/api/v1/categories/", json=payload, headers=admin_headers)

    assert response.status_code == 422


def test_list_categories_returns_multiple_categories(client, admin_headers):
    categories = [
        {
            "name": "Wet Dog Food",
            "slug": "wet-dog-food",
            "description": "Wet food for dogs",
            "parent_id": None,
        },
        {
            "name": "Puppy Food",
            "slug": "puppy-food",
            "description": "Food for puppies",
            "parent_id": None,
        },
    ]

    for category in categories:
        response = client.post("/api/v1/categories/", json=category, headers=admin_headers)
        assert response.status_code == 201

    response = client.get("/api/v1/categories/", headers=admin_headers)

    assert response.status_code == 200
    result = response.json()
    assert len(result) == 2
    assert {item["slug"] for item in result} == {
        "wet-dog-food",
        "puppy-food",
    }


def test_list_categories_excludes_soft_deleted_categories(client, db_session, admin_headers):
    from datetime import datetime, timezone

    from app.models.models import Category

    deleted_category = Category(
        name="Deleted Dog Food",
        slug="deleted-dog-food",
        description="This category should not appear",
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add(deleted_category)
    db_session.flush()

    response = client.get("/api/v1/categories/", headers=admin_headers)

    assert response.status_code == 200
    assert "deleted-dog-food" not in {
        item["slug"] for item in response.json()
    }

def test_create_category_handles_database_integrity_error(client, admin_headers):
    payload = {
        "name": "Conflict Category",
        "slug": "conflict-category",
        "description": None,
        "parent_id": None,
    }

    with patch(
        "app.api.v1.categories.create_category_service",
        side_effect=IntegrityError(
            "INSERT",
            {},
            Exception("Simulated database constraint violation"),
        ),
    ):
        response = client.post("/api/v1/categories/", json=payload, headers=admin_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Category conflicts with an existing database record."
    )
