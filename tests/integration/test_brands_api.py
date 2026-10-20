import pytest
from unittest.mock import patch
from sqlalchemy.exc import IntegrityError

def test_list_brands_returns_empty_list(client):
    response = client.get("/api/v1/brands/")

    assert response.status_code == 200
    assert response.json() == []


def test_create_brand_returns_created_response(client, admin_headers):
    payload = {
        "name": "Paw Nutrition",
        "slug": "paw-nutrition",
        "description": "Nutrition products for dogs",
    }

    response = client.post("/api/v1/brands/", json=payload, headers=admin_headers)

    assert response.status_code == 201
    data = response.json()
    assert isinstance(data["id"], int)
    assert data["name"] == payload["name"]
    assert data["slug"] == payload["slug"]
    assert data["description"] == payload["description"]
    assert "created_at" in data


def test_create_brand_rejects_invalid_slug(client, admin_headers):
    payload = {
        "name": "Invalid Brand",
        "slug": "Invalid Brand!",
        "description": None,
    }

    response = client.post("/api/v1/brands/", json=payload, headers=admin_headers)

    assert response.status_code == 422


def test_create_brand_rejects_duplicate_slug(client, admin_headers):
    payload = {
        "name": "Paw Nutrition",
        "slug": "paw-nutrition",
        "description": None,
    }

    first_response = client.post("/api/v1/brands/", json=payload, headers=admin_headers)
    second_response = client.post("/api/v1/brands/", json=payload, headers=admin_headers)

    assert first_response.status_code == 201
    assert second_response.status_code in (400, 409)


def test_create_brand_rejects_name_that_is_too_short(client, admin_headers):
    payload = {
        "name": "A",
        "slug": "short-brand",
        "description": None,
    }

    response = client.post("/api/v1/brands/", json=payload, headers=admin_headers)

    assert response.status_code == 422


def test_create_brand_rejects_missing_name(client, admin_headers):
    payload = {
        "slug": "missing-brand-name",
        "description": None,
    }

    response = client.post("/api/v1/brands/", json=payload, headers=admin_headers)

    assert response.status_code == 422

def test_create_brand_handles_database_integrity_error(client, admin_headers):
    payload = {
        "name": "Conflict Brand",
        "slug": "conflict-brand",
        "description": None,
    }

    with patch(
        "app.api.v1.brands.create_brand_service",
        side_effect=IntegrityError(
            "INSERT",
            {},
            Exception("Simulated database constraint violation"),
        ),
    ):
        response = client.post("/api/v1/brands/", json=payload, headers=admin_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Brand conflicts with an existing database record."
    )


def test_create_brand_rolls_back_on_database_error(db_session, admin_headers):
    from unittest.mock import patch

    from app.repositories.brand_repository import create_brand
    from app.schemas.brand import BrandCreate

    brand_data = BrandCreate(
        name="Rollback Brand",
        slug="rollback-brand",
        description=None,
    )

    with patch.object(db_session, "commit", side_effect=RuntimeError("Simulated database failure")):
        with pytest.raises(RuntimeError, match="Simulated database failure"):
            create_brand(db_session, brand_data)

    assert not db_session.new


def test_get_brand_by_id_returns_brand(client, admin_headers):
    payload = {
        "name": "Single Brand",
        "slug": "single-brand",
        "description": "A test brand",
    }

    create_response = client.post("/api/v1/brands/", json=payload, headers=admin_headers)
    assert create_response.status_code == 201
    brand_id = create_response.json()["id"]

    response = client.get(f"/api/v1/brands/{brand_id}", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["id"] == brand_id
    assert response.json()["name"] == payload["name"]


def test_get_brand_by_id_returns_404_for_missing_brand(client, admin_headers):
    response = client.get("/api/v1/brands/999999999", headers=admin_headers)

    assert response.status_code == 404


def test_update_brand_successfully(client, admin_headers):
    create_response = client.post(
        "/api/v1/brands/",
        json={
            "name": "Original Brand",
            "slug": "original-brand",
            "description": "Original description",
        },
        headers=admin_headers,
    )
    assert create_response.status_code == 201
    brand_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/brands/{brand_id}",
        json={
            "name": "Updated Brand",
            "description": "Updated description",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Brand"
    assert response.json()["slug"] == "original-brand"
    assert response.json()["description"] == "Updated description"


def test_update_brand_returns_404_for_missing_brand(client, admin_headers):
    response = client.patch(
        "/api/v1/brands/999999999",
        json={"name": "Updated Brand"},
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_update_brand_rejects_invalid_slug(client, admin_headers):
    create_response = client.post(
        "/api/v1/brands/",
        json={
            "name": "Valid Brand",
            "slug": "valid-brand",
            "description": None,
        },
        headers=admin_headers,
    )
    assert create_response.status_code == 201
    brand_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/brands/{brand_id}",
        json={"slug": "Invalid Slug!"},
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_update_brand_rejects_duplicate_slug(client, admin_headers):
    first_response = client.post(
        "/api/v1/brands/",
        json={
            "name": "First Brand",
            "slug": "first-brand",
            "description": None,
        },
        headers=admin_headers,
    )
    second_response = client.post(
        "/api/v1/brands/",
        json={
            "name": "Second Brand",
            "slug": "second-brand",
            "description": None,
        },
        headers=admin_headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    second_id = second_response.json()["id"]

    response = client.patch(
        f"/api/v1/brands/{second_id}",
        json={"slug": "first-brand"},
        headers=admin_headers,
    )

    assert response.status_code == 409


def test_update_brand_rejects_null_name(client, admin_headers):
    create_response = client.post(
        "/api/v1/brands/",
        json={
            "name": "Null Test Brand",
            "slug": "null-test-brand",
            "description": None,
        },
        headers=admin_headers,  
    )
    assert create_response.status_code == 201
    brand_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/brands/{brand_id}",
        json={"name": None},
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_update_brand_rejects_null_slug(client, admin_headers):
    create_response = client.post(
        "/api/v1/brands/",
        json={
            "name": "Null Slug Brand",
            "slug": "null-slug-brand",
            "description": None,
        },
        headers=admin_headers,
    )
    assert create_response.status_code == 201
    brand_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/brands/{brand_id}",
        json={"slug": None},
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_update_brand_allows_keeping_its_own_slug(client, admin_headers):
    create_response = client.post(
        "/api/v1/brands/",
        json={
            "name": "Keep Slug Brand",
            "slug": "keep-slug-brand",
            "description": None,
        },
        headers=admin_headers,
    )
    assert create_response.status_code == 201
    brand_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/brands/{brand_id}",
        json={"slug": "keep-slug-brand"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["slug"] == "keep-slug-brand"


def test_delete_brand_soft_deletes_brand(client, admin_headers):
    create_response = client.post(
        "/api/v1/brands/",
        json={
            "name": "Delete Test Brand",
            "slug": "delete-test-brand",
            "description": "Brand to delete",
        },
        headers=admin_headers,
    )
    assert create_response.status_code == 201
    brand_id = create_response.json()["id"]

    response = client.delete(f"/api/v1/brands/{brand_id}", headers=admin_headers)

    assert response.status_code == 204

    get_response = client.get(f"/api/v1/brands/{brand_id}", headers=admin_headers)
    assert get_response.status_code == 404

    list_response = client.get("/api/v1/brands/", headers=admin_headers)
    assert all(
        brand["id"] != brand_id
        for brand in list_response.json()
    )


def test_delete_brand_returns_404_for_missing_brand(client, admin_headers):
    response = client.delete("/api/v1/brands/999999999", headers=admin_headers)

    assert response.status_code == 404


def test_update_brand_handles_database_integrity_error(client, admin_headers):
    create_response = client.post(
        "/api/v1/brands/",
        json={
            "name": "Update Error Brand",
            "slug": "update-error-brand",
        },
        headers=admin_headers,
    )
    assert create_response.status_code == 201
    brand_id = create_response.json()["id"]

    # Patch the function where the service actually looks it up.
    with patch(
        "app.services.brand_service.update_brand",
        side_effect=IntegrityError(
            "UPDATE", {}, Exception("database error")
        ),
    ):
        response = client.patch(
            f"/api/v1/brands/{brand_id}",
            json={"name": "Updated Error Brand"},
            headers=admin_headers,
        )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Brand conflicts with an existing database record."
    )


def test_update_brand_repository_rolls_back_on_error(db_session):
    from app.models.models import Brand
    from app.repositories.brand_repository import update_brand

    brand = Brand(name="Rollback Brand", slug="rollback-brand")
    db_session.add(brand)
    db_session.flush()

    with patch.object(
        db_session, "commit", side_effect=RuntimeError("commit failed")
    ):
        with patch.object(
            db_session, "rollback", wraps=db_session.rollback
        ) as rollback_mock:
            with pytest.raises(RuntimeError, match="commit failed"):
                update_brand(db_session, brand, {"name": "Changed Name"})

            rollback_mock.assert_called_once()


def test_soft_delete_brand_repository_rolls_back_on_error(db_session):
    from app.models.models import Brand
    from app.repositories.brand_repository import soft_delete_brand

    brand = Brand(name="Delete Rollback Brand", slug="delete-rollback-brand")
    db_session.add(brand)
    db_session.flush()

    with patch.object(
        db_session, "commit", side_effect=RuntimeError("commit failed")
    ):
        with patch.object(
            db_session, "rollback", wraps=db_session.rollback
        ) as rollback_mock:
            with pytest.raises(RuntimeError, match="commit failed"):
                soft_delete_brand(db_session, brand)

            rollback_mock.assert_called_once()
