
from datetime import datetime, timezone
import uuid

import pytest

from app.models.models import (
    Category,
    Product,
    ProductStatus,
    ProductVariant,
)


@pytest.fixture
def product_category(db_session):
    category = Category(
        name="Test Dog Food",
        slug=f"test-dog-food-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(category)
    db_session.flush()
    return category


@pytest.fixture
def draft_product(db_session, product_category):
    product = Product(
        category_id=product_category.id,
        name="Test Puppy Food",
        slug=f"test-puppy-food-{uuid.uuid4().hex[:8]}",
        status=ProductStatus.DRAFT,
    )
    db_session.add(product)
    db_session.flush()
    return product


def test_admin_can_create_product(client, admin_headers, product_category):
    response = client.post(
        "/api/v1/products/",
        headers=admin_headers,
        json={
            "category_id": product_category.id,
            "name": "Chicken Puppy Food",
            "slug": f"chicken-puppy-food-{uuid.uuid4().hex[:8]}",
            "description": "Complete food for puppies",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Chicken Puppy Food"
    assert response.json()["status"] == "draft"


def test_public_cannot_see_draft_products(client, draft_product):
    response = client.get("/api/v1/products/")

    assert response.status_code == 200
    assert all(
        item["id"] != str(draft_product.id)
        for item in response.json()
    )


def test_public_gets_404_for_draft_product(client, draft_product):
    response = client.get(f"/api/v1/products/{draft_product.id}")

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("method", "url_suffix", "payload"),
    [
        (
            "post",
            "/",
            {"name": "Unauthorized Food", "slug": "unauthorized-food"},
        ),
        (
            "patch",
            None,
            {"name": "Updated Food"},
        ),
        ("delete", None, None),
    ],
)
def test_anonymous_cannot_modify_products(
    client, draft_product, method, url_suffix, payload
):
    url = (
        f"/api/v1/products/{draft_product.id}"
        if url_suffix is None
        else f"/api/v1/products{url_suffix}"
    )

    if payload is None:
        response = getattr(client, method)(url)
    else:
        body = dict(payload)
        if method == "post":
            body["category_id"] = draft_product.category_id
        response = getattr(client, method)(url, json=body)

    assert response.status_code == 401


def test_admin_can_update_product(client, admin_headers, draft_product):
    response = client.patch(
        f"/api/v1/products/{draft_product.id}",
        headers=admin_headers,
        json={"name": "Updated Puppy Food"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Puppy Food"


def test_admin_can_soft_delete_product(client, admin_headers, draft_product):
    response = client.delete(
        f"/api/v1/products/{draft_product.id}",
        headers=admin_headers,
    )

    assert response.status_code == 204

    get_response = client.get(f"/api/v1/products/{draft_product.id}")
    assert get_response.status_code == 404


def test_regular_user_cannot_create_product(
    client, user_headers, product_category
):
    response = client.post(
        "/api/v1/products/",
        headers=user_headers,
        json={
            "category_id": product_category.id,
            "name": "Regular User Food",
            "slug": f"regular-user-food-{uuid.uuid4().hex[:8]}",
        },
    )

    assert response.status_code == 403


def test_admin_cannot_create_product_with_duplicate_slug(
    client, admin_headers, product_category
):
    slug = f"duplicate-product-{uuid.uuid4().hex[:8]}"
    payload = {
        "category_id": product_category.id,
        "name": "First Test Product",
        "slug": slug,
    }

    first_response = client.post(
        "/api/v1/products/",
        headers=admin_headers,
        json=payload,
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/api/v1/products/",
        headers=admin_headers,
        json={
            **payload,
            "name": "Second Test Product",
        },
    )

    assert second_response.status_code == 400


def test_admin_cannot_create_product_with_invalid_category(
    client, admin_headers
):
    response = client.post(
        "/api/v1/products/",
        headers=admin_headers,
        json={
            "category_id": 999999999,
            "name": "Invalid Category Product",
            "slug": f"invalid-category-{uuid.uuid4().hex[:8]}",
        },
    )

    assert response.status_code == 400


def test_public_product_returns_only_active_variants(
    client, db_session, product_category
):
    product = Product(
        category_id=product_category.id,
        name="Variant Test Dog Food",
        slug=f"variant-test-food-{uuid.uuid4().hex[:8]}",
        status=ProductStatus.ACTIVE,
    )
    db_session.add(product)
    db_session.flush()

    active_variant = ProductVariant(
        product_id=product.id,
        sku=f"TEST-1KG-{uuid.uuid4().hex[:8]}",
        variant_name="1 kg",
        weight_grams=1000,
        price=499.00,
        currency="INR",
        is_active=True,
    )

    inactive_variant = ProductVariant(
        product_id=product.id,
        sku=f"TEST-3KG-{uuid.uuid4().hex[:8]}",
        variant_name="3 kg",
        weight_grams=3000,
        price=1299.00,
        currency="INR",
        is_active=False,
    )

    deleted_variant = ProductVariant(
        product_id=product.id,
        sku=f"TEST-7KG-{uuid.uuid4().hex[:8]}",
        variant_name="7 kg",
        weight_grams=7000,
        price=2499.00,
        currency="INR",
        is_active=True,
        deleted_at=datetime.now(timezone.utc),
    )

    db_session.add_all(
        [active_variant, inactive_variant, deleted_variant]
    )
    db_session.commit()

    response = client.get(f"/api/v1/products/{product.id}")

    assert response.status_code == 200

    variants = response.json()["variants"]

    assert len(variants) == 1
    assert variants[0]["variant_name"] == "1 kg"
    assert variants[0]["weight_grams"] == 1000
    assert float(variants[0]["price"]) == 499.00
    assert variants[0]["currency"] == "INR"


def test_public_can_search_products(client, db_session, product_category):
    matching = Product(
        category_id=product_category.id,
        name="Chicken Puppy Food",
        slug=f"chicken-food-{uuid.uuid4().hex[:8]}",
        status=ProductStatus.ACTIVE,
    )
    non_matching = Product(
        category_id=product_category.id,
        name="Salmon Adult Food",
        slug=f"salmon-food-{uuid.uuid4().hex[:8]}",
        status=ProductStatus.ACTIVE,
    )
    db_session.add_all([matching, non_matching])
    db_session.flush()

    response = client.get("/api/v1/products/?search=Chicken")

    assert response.status_code == 200
    results = response.json()

    assert any(
        item["id"] == str(matching.id)
        for item in results
    )
    assert all(
        item["id"] != str(non_matching.id)
        for item in results
    )
    assert all(
        "chicken" in item["name"].lower()
        or "chicken" in (item["short_description"] or "").lower()
        or "chicken" in (item["description"] or "").lower()
        for item in results
    )


def test_public_can_filter_products_by_category(
    client, db_session, product_category
):
    other_category = Category(
        name="Other Test Category",
        slug=f"other-category-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(other_category)
    db_session.flush()

    matching = Product(
        category_id=product_category.id,
        name="Category Match Food",
        slug=f"category-match-{uuid.uuid4().hex[:8]}",
        status=ProductStatus.ACTIVE,
    )
    other = Product(
        category_id=other_category.id,
        name="Category Other Food",
        slug=f"category-other-{uuid.uuid4().hex[:8]}",
        status=ProductStatus.ACTIVE,
    )
    db_session.add_all([matching, other])
    db_session.flush()

    response = client.get(
        f"/api/v1/products/?category_id={product_category.id}"
    )

    assert response.status_code == 200
    results = response.json()

    assert any(
        item["id"] == str(matching.id)
        for item in results
    )
    assert all(
        item["category_id"] == product_category.id
        for item in results
    )


def test_public_can_sort_products_by_name(
    client, db_session, product_category
):
    products = [
        Product(
            category_id=product_category.id,
            name=name,
            slug=f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}",
            status=ProductStatus.ACTIVE,
        )
        for name in ["Zebra Food", "Apple Food"]
    ]
    db_session.add_all(products)
    db_session.flush()

    response = client.get(
        "/api/v1/products/?sort_by=name&sort_order=asc"
    )

    assert response.status_code == 200
    names = [item["name"] for item in response.json()]
    assert names == sorted(names)
