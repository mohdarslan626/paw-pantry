
import pytest


@pytest.mark.parametrize(
    ("method", "url", "payload"),
    [
        (
            "post",
            "/api/v1/brands/",
            {"name": "Test Brand", "slug": "test-brand"},
        ),
        (
            "patch",
            "/api/v1/brands/1",
            {"name": "Updated Brand"},
        ),
        (
            "delete",
            "/api/v1/brands/1",
            None,
        ),
        (
            "post",
            "/api/v1/categories/",
            {"name": "Test Category", "slug": "test-category"},
        ),
    ],
)
def test_anonymous_users_cannot_modify_catalog(
    client, method, url, payload
):
    response = getattr(client, method)(
        url,
        json=payload,
    ) if payload is not None else getattr(client, method)(url)

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("method", "url", "payload"),
    [
        (
            "post",
            "/api/v1/brands/",
            {"name": "Regular User Brand", "slug": "regular-user-brand"},
        ),
        (
            "patch",
            "/api/v1/brands/1",
            {"name": "Updated Brand"},
        ),
        (
            "delete",
            "/api/v1/brands/1",
            None,
        ),
        (
            "post",
            "/api/v1/categories/",
            {"name": "Regular User Category", "slug": "regular-user-category"},
        ),
    ],
)
def test_regular_users_cannot_modify_catalog(
    client, user_headers, method, url, payload
):
    response = (
        getattr(client, method)(url, json=payload, headers=user_headers)
        if payload is not None
        else getattr(client, method)(url, headers=user_headers)
    )

    assert response.status_code == 403


def test_admin_can_create_brand(client, admin_headers):
    response = client.post(
        "/api/v1/brands/",
        json={
            "name": "Admin Test Brand",
            "slug": "admin-test-brand",
            "description": "Created by an admin test",
        },
        headers=admin_headers,
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Admin Test Brand"


def test_admin_can_create_category(client, admin_headers):
    response = client.post(
        "/api/v1/categories/",
        json={
            "name": "Admin Test Category",
            "slug": "admin-test-category",
            "description": "Created by an admin test",
        },
        headers=admin_headers,
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Admin Test Category"


def test_admin_can_update_brand(client, admin_headers):
    create_response = client.post(
        "/api/v1/brands/",
        json={"name": "Update Test Brand", "slug": "update-test-brand"},
        headers=admin_headers,
    )
    assert create_response.status_code == 201
    brand_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/brands/{brand_id}",
        json={"name": "Updated Test Brand"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Test Brand"


def test_admin_can_delete_brand(client, admin_headers):
    create_response = client.post(
        "/api/v1/brands/",
        json={"name": "Delete Test Brand", "slug": "delete-test-brand"},
        headers=admin_headers,
    )
    assert create_response.status_code == 201
    brand_id = create_response.json()["id"]

    response = client.delete(
        f"/api/v1/brands/{brand_id}",
        headers=admin_headers,
    )

    assert response.status_code in (200, 204)
