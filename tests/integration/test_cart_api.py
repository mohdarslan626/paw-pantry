from app.models.models import (
    Inventory,
    InventoryLocation,
    Order,
    OrderItem,
    UserAddress,
)

import uuid
from decimal import Decimal

import pytest

from app.models.models import (
    Cart,
    CartItem,
    Category,
    Product,
    ProductStatus,
    ProductVariant,
)


@pytest.fixture
def cart_variant(db_session):
    category = Category(
        name="Cart Test Category",
        slug=f"cart-category-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(category)
    db_session.flush()

    product = Product(
        category_id=category.id,
        name="Cart Test Food",
        slug=f"cart-food-{uuid.uuid4().hex[:8]}",
        status=ProductStatus.ACTIVE,
    )
    db_session.add(product)
    db_session.flush()

    variant = ProductVariant(
        product_id=product.id,
        sku=f"CART-{uuid.uuid4().hex[:8]}",
        variant_name="1 kg",
        weight_grams=1000,
        price=Decimal("499.00"),
        currency="INR",
        is_active=True,
    )
    db_session.add(variant)
    db_session.flush()

    return variant


def test_anonymous_cannot_access_cart(client):
    response = client.get("/api/v1/cart/")
    assert response.status_code == 401


def test_user_can_get_empty_cart(client, user_headers):
    response = client.get(
        "/api/v1/cart/",
        headers=user_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert Decimal(body["subtotal"]) == Decimal("0")


def test_user_can_add_variant_to_cart(
    client, user_headers, cart_variant
):
    response = client.post(
        "/api/v1/cart/items",
        headers=user_headers,
        json={
            "variant_id": str(cart_variant.id),
            "quantity": 2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 2
    assert Decimal(body["items"][0]["unit_price"]) == Decimal("499.00")
    assert Decimal(body["subtotal"]) == Decimal("998.00")


def test_adding_same_variant_increases_quantity(
    client, user_headers, cart_variant
):
    url = "/api/v1/cart/items"
    headers = user_headers
    payload = {
        "variant_id": str(cart_variant.id),
        "quantity": 2,
    }

    first = client.post(url, headers=headers, json=payload)
    second = client.post(
        url,
        headers=headers,
        json={
            "variant_id": str(cart_variant.id),
            "quantity": 3,
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(second.json()["items"]) == 1
    assert second.json()["items"][0]["quantity"] == 5
    assert Decimal(second.json()["subtotal"]) == Decimal("2495.00")


def test_user_can_update_cart_quantity(
    client, user_headers, cart_variant
):
    added = client.post(
        "/api/v1/cart/items",
        headers=user_headers,
        json={
            "variant_id": str(cart_variant.id),
            "quantity": 1,
        },
    )
    assert added.status_code == 200

    item_id = added.json()["items"][0]["id"]
    response = client.patch(
        f"/api/v1/cart/items/{item_id}",
        headers=user_headers,
        json={"quantity": 4},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["quantity"] == 4
    assert Decimal(response.json()["subtotal"]) == Decimal("1996.00")


def test_user_can_remove_cart_item(
    client, user_headers, cart_variant
):
    added = client.post(
        "/api/v1/cart/items",
        headers=user_headers,
        json={
            "variant_id": str(cart_variant.id),
            "quantity": 1,
        },
    )
    assert added.status_code == 200

    item_id = added.json()["items"][0]["id"]
    response = client.delete(
        f"/api/v1/cart/items/{item_id}",
        headers=user_headers,
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert Decimal(response.json()["subtotal"]) == Decimal("0")


def test_user_cannot_update_another_users_cart_item(
    client, user_headers, admin_headers, cart_variant
):
    added = client.post(
        "/api/v1/cart/items",
        headers=user_headers,
        json={
            "variant_id": str(cart_variant.id),
            "quantity": 1,
        },
    )
    assert added.status_code == 200

    item_id = added.json()["items"][0]["id"]
    response = client.patch(
        f"/api/v1/cart/items/{item_id}",
        headers=admin_headers,
        json={"quantity": 3},
    )

    assert response.status_code == 404


def test_removed_variant_can_be_added_again(
    client, user_headers, cart_variant, db_session
):
    added = client.post(
        "/api/v1/cart/items",
        headers=user_headers,
        json={
            "variant_id": str(cart_variant.id),
            "quantity": 2,
        },
    )
    assert added.status_code == 200

    item_id = added.json()["items"][0]["id"]
    removed = client.delete(
        f"/api/v1/cart/items/{item_id}",
        headers=user_headers,
    )
    assert removed.status_code == 200

    restored = client.post(
        "/api/v1/cart/items",
        headers=user_headers,
        json={
            "variant_id": str(cart_variant.id),
            "quantity": 3,
        },
    )

    assert restored.status_code == 200
    assert len(restored.json()["items"]) == 1
    assert restored.json()["items"][0]["id"] == item_id
    assert restored.json()["items"][0]["quantity"] == 3

    db_session.expire_all()
    saved_item = db_session.get(CartItem, uuid.UUID(item_id))
    assert saved_item is not None
    assert saved_item.deleted_at is None


def test_inactive_variant_cannot_be_added(
    client, user_headers, cart_variant, db_session
):
    cart_variant.is_active = False
    db_session.flush()

    response = client.post(
        "/api/v1/cart/items",
        headers=user_headers,
        json={
            "variant_id": str(cart_variant.id),
            "quantity": 1,
        },
    )

    assert response.status_code == 400



def test_user_can_checkout_with_sufficient_inventory(
    client, user_headers, cart_variant, db_session
):
    import uuid

    from decimal import Decimal

    # Find the authenticated user's ID from the existing test fixture.
    from app.core.security import decode_access_token

    token = user_headers["Authorization"].split(" ", 1)[1]
    user_id = uuid.UUID(decode_access_token(token)["sub"])

    address = UserAddress(
        user_id=user_id,
        address_type="shipping",
        recipient_name="Test Customer",
        phone="9999999999",
        line1="123 Test Street",
        city="Meerut",
        state_region="Uttar Pradesh",
        postal_code="250001",
        country_code="IN",
    )
    db_session.add(address)

    location = InventoryLocation(
        code=f"TEST-{uuid.uuid4().hex[:8]}",
        name="Test Warehouse",
    )
    db_session.add(location)
    db_session.flush()

    inventory = Inventory(
        variant_id=cart_variant.id,
        location_id=location.id,
        on_hand=10,
        reserved=0,
    )
    db_session.add(inventory)
    db_session.flush()

    added = client.post(
        "/api/v1/cart/items",
        headers=user_headers,
        json={
            "variant_id": str(cart_variant.id),
            "quantity": 2,
        },
    )
    assert added.status_code == 200

    response = client.post(
        "/api/v1/orders/checkout",
        headers=user_headers,
        json={
            "shipping_address_id": str(address.id),
            "idempotency_key": f"checkout-{uuid.uuid4().hex}",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()

    assert body["status"] == "pending"
    assert body["currency"] == "INR"
    assert Decimal(body["subtotal_amount"]) == Decimal("998.00")
    assert Decimal(body["total_amount"]) == Decimal("998.00")
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 2

    db_session.expire_all()

    saved_order = db_session.get(Order, uuid.UUID(body["id"]))
    assert saved_order is not None
    assert saved_order.status.value == "pending"

    saved_items = (
        db_session.query(OrderItem)
        .filter(
            OrderItem.order_id == saved_order.id,
            OrderItem.deleted_at.is_(None),
        )
        .all()
    )
    assert len(saved_items) == 1

    saved_inventory = (
        db_session.query(Inventory)
        .filter(
            Inventory.variant_id == cart_variant.id,
            Inventory.location_id == location.id,
        )
        .one()
    )
    assert saved_inventory.on_hand == 10
    assert saved_inventory.reserved == 2



def test_checkout_retry_does_not_create_duplicate_order(
    client, user_headers, cart_variant, db_session
):
    import uuid

    from app.core.security import decode_access_token
    from app.models.models import (
        Inventory,
        InventoryLocation,
        Order,
        UserAddress,
    )

    token = user_headers["Authorization"].split(" ", 1)[1]
    user_id = uuid.UUID(decode_access_token(token)["sub"])

    address = UserAddress(
        user_id=user_id,
        address_type="shipping",
        recipient_name="Test Customer",
        line1="123 Test Street",
        city="Meerut",
        state_region="Uttar Pradesh",
        postal_code="250001",
        country_code="IN",
    )
    db_session.add(address)

    location = InventoryLocation(
        code=f"TEST-{uuid.uuid4().hex[:8]}",
        name="Test Warehouse",
    )
    db_session.add(location)
    db_session.flush()

    db_session.add(
        Inventory(
            variant_id=cart_variant.id,
            location_id=location.id,
            on_hand=10,
            reserved=0,
        )
    )
    db_session.flush()

    added = client.post(
        "/api/v1/cart/items",
        headers=user_headers,
        json={"variant_id": str(cart_variant.id), "quantity": 2},
    )
    assert added.status_code == 200

    key = f"checkout-{uuid.uuid4().hex}"
    payload = {
        "shipping_address_id": str(address.id),
        "idempotency_key": key,
    }

    first = client.post(
        "/api/v1/orders/checkout",
        headers=user_headers,
        json=payload,
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/orders/checkout",
        headers=user_headers,
        json=payload,
    )
    assert second.status_code == 201, second.text
    assert second.json()["id"] == first.json()["id"]

    db_session.expire_all()

    orders = (
        db_session.query(Order)
        .filter(Order.user_id == user_id, Order.deleted_at.is_(None))
        .all()
    )
    assert len(orders) == 1


def test_checkout_rejects_insufficient_inventory(
    client, user_headers, cart_variant, db_session
):
    import uuid
    from decimal import Decimal

    from app.core.security import decode_access_token
    from app.models.models import (
        Inventory,
        InventoryLocation,
        Order,
        UserAddress,
    )

    token = user_headers["Authorization"].split(" ", 1)[1]
    user_id = uuid.UUID(decode_access_token(token)["sub"])

    address = UserAddress(
        user_id=user_id,
        address_type="shipping",
        recipient_name="Test Customer",
        line1="123 Test Street",
        city="Meerut",
        state_region="Uttar Pradesh",
        postal_code="250001",
        country_code="IN",
    )
    db_session.add(address)

    location = InventoryLocation(
        code=f"TEST-{uuid.uuid4().hex[:8]}",
        name="Test Warehouse",
    )
    db_session.add(location)
    db_session.flush()

    db_session.add(
        Inventory(
            variant_id=cart_variant.id,
            location_id=location.id,
            on_hand=1,
            reserved=0,
        )
    )
    db_session.flush()

    added = client.post(
        "/api/v1/cart/items",
        headers=user_headers,
        json={
            "variant_id": str(cart_variant.id),
            "quantity": 2,
        },
    )
    assert added.status_code == 200

    response = client.post(
        "/api/v1/orders/checkout",
        headers=user_headers,
        json={
            "shipping_address_id": str(address.id),
            "idempotency_key": f"checkout-{uuid.uuid4().hex}",
        },
    )

    assert response.status_code == 409
    assert "insufficient stock" in response.json()["detail"].lower()

    db_session.expire_all()

    saved_inventory = (
        db_session.query(Inventory)
        .filter(
            Inventory.variant_id == cart_variant.id,
            Inventory.location_id == location.id,
        )
        .one()
    )
    assert saved_inventory.on_hand == 1
    assert saved_inventory.reserved == 0

    saved_orders = (
        db_session.query(Order)
        .filter(
            Order.user_id == user_id,
            Order.deleted_at.is_(None),
        )
        .all()
    )
    assert saved_orders == []


def test_checkout_rejects_another_users_shipping_address(
    client, user_headers, admin_headers, cart_variant, db_session
):
    import uuid

    from app.core.security import decode_access_token
    from app.models.models import (
        Inventory,
        InventoryLocation,
        Order,
        UserAddress,
    )

    other_token = admin_headers["Authorization"].split(" ", 1)[1]
    other_user_id = uuid.UUID(
        decode_access_token(other_token)["sub"]
    )

    address = UserAddress(
        user_id=other_user_id,
        address_type="shipping",
        recipient_name="Another Customer",
        line1="456 Other Street",
        city="Meerut",
        state_region="Uttar Pradesh",
        postal_code="250002",
        country_code="IN",
    )
    db_session.add(address)

    location = InventoryLocation(
        code=f"TEST-{uuid.uuid4().hex[:8]}",
        name="Test Warehouse",
    )
    db_session.add(location)
    db_session.flush()

    db_session.add(
        Inventory(
            variant_id=cart_variant.id,
            location_id=location.id,
            on_hand=10,
            reserved=0,
        )
    )
    db_session.flush()

    added = client.post(
        "/api/v1/cart/items",
        headers=user_headers,
        json={
            "variant_id": str(cart_variant.id),
            "quantity": 1,
        },
    )
    assert added.status_code == 200

    response = client.post(
        "/api/v1/orders/checkout",
        headers=user_headers,
        json={
            "shipping_address_id": str(address.id),
            "idempotency_key": f"checkout-{uuid.uuid4().hex}",
        },
    )

    assert response.status_code == 404
    assert "address not found" in response.json()["detail"].lower()

    # Checkout should not create an order for the requesting user.
    token = user_headers["Authorization"].split(" ", 1)[1]
    user_id = uuid.UUID(decode_access_token(token)["sub"])

    db_session.expire_all()
    orders = (
        db_session.query(Order)
        .filter(
            Order.user_id == user_id,
            Order.deleted_at.is_(None),
        )
        .all()
    )
    assert orders == []
