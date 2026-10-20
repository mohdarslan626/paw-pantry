
import uuid
from decimal import Decimal

import pytest

from app.models.models import Category, Product, ProductStatus, ProductVariant


@pytest.fixture
def variant_product(db_session):
    category = Category(
        name="Variant Test Category",
        slug=f"variant-category-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(category)
    db_session.flush()

    product = Product(
        category_id=category.id,
        name="Variant Test Food",
        slug=f"variant-food-{uuid.uuid4().hex[:8]}",
        status=ProductStatus.ACTIVE,
    )
    db_session.add(product)
    db_session.flush()
    return product


def variant_payload(sku=None):
    return {
        "sku": sku or f"TEST-{uuid.uuid4().hex[:8]}",
        "variant_name": "1 kg",
        "weight_grams": 1000,
        "price": "499.00",
        "currency": "INR",
        "is_active": True,
    }


def test_admin_can_create_product_variant(
    client, admin_headers, variant_product
):
    response = client.post(
        f"/api/v1/products/{variant_product.id}/variants/",
        headers=admin_headers,
        json=variant_payload(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["variant_name"] == "1 kg"
    assert body["weight_grams"] == 1000
    assert Decimal(body["price"]) == Decimal("499.00")
    assert body["currency"] == "INR"


def test_admin_can_update_variant_price(
    client, admin_headers, variant_product, db_session
):
    variant = ProductVariant(
        product_id=variant_product.id,
        **variant_payload(),
    )
    db_session.add(variant)
    db_session.flush()

    response = client.patch(
        f"/api/v1/products/{variant_product.id}/variants/{variant.id}",
        headers=admin_headers,
        json={"price": "549.00"},
    )

    assert response.status_code == 200
    assert Decimal(response.json()["price"]) == Decimal("549.00")


def test_admin_can_soft_delete_variant(
    client, admin_headers, variant_product, db_session
):
    variant = ProductVariant(
        product_id=variant_product.id,
        **variant_payload(),
    )
    db_session.add(variant)
    db_session.flush()

    response = client.delete(
        f"/api/v1/products/{variant_product.id}/variants/{variant.id}",
        headers=admin_headers,
    )

    assert response.status_code == 204
    assert variant.deleted_at is not None


@pytest.mark.parametrize(
    ("method", "suffix", "payload"),
    [
        ("post", "/", "create"),
        ("patch", None, {"price": "599.00"}),
        ("delete", None, None),
    ],
)
def test_anonymous_cannot_modify_variants(
    client, variant_product, method, suffix, payload, db_session
):
    variant = ProductVariant(
        product_id=variant_product.id,
        **variant_payload(),
    )
    db_session.add(variant)
    db_session.flush()

    url = (
        f"/api/v1/products/{variant_product.id}/variants/"
        if suffix == "/"
        else f"/api/v1/products/{variant_product.id}/variants/{variant.id}"
    )

    if method == "post":
        response = client.post(url, json=variant_payload())
    elif method == "patch":
        response = client.patch(url, json=payload)
    else:
        response = client.delete(url)

    assert response.status_code == 401


def test_regular_user_cannot_create_variant(
    client, user_headers, variant_product
):
    response = client.post(
        f"/api/v1/products/{variant_product.id}/variants/",
        headers=user_headers,
        json=variant_payload(),
    )

    assert response.status_code == 403


def test_duplicate_sku_returns_conflict(
    client, admin_headers, variant_product, db_session
):
    sku = f"DUP-{uuid.uuid4().hex[:8]}"

    existing = ProductVariant(
        product_id=variant_product.id,
        **variant_payload(sku),
    )
    db_session.add(existing)
    db_session.flush()

    response = client.post(
        f"/api/v1/products/{variant_product.id}/variants/",
        headers=admin_headers,
        json=variant_payload(sku),
    )

    assert response.status_code == 409


def test_variant_cannot_be_updated_through_another_product(
    client, admin_headers, variant_product, db_session
):
    other_category = Category(
        name="Another Test Category",
        slug=f"another-category-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(other_category)
    db_session.flush()

    other_product = Product(
        category_id=other_category.id,
        name="Another Test Food",
        slug=f"another-food-{uuid.uuid4().hex[:8]}",
        status=ProductStatus.ACTIVE,
    )
    db_session.add(other_product)
    db_session.flush()

    variant = ProductVariant(
        product_id=variant_product.id,
        **variant_payload(),
    )
    db_session.add(variant)
    db_session.flush()

    response = client.patch(
        f"/api/v1/products/{other_product.id}/variants/{variant.id}",
        headers=admin_headers,
        json={"price": "599.00"},
    )

    assert response.status_code == 404