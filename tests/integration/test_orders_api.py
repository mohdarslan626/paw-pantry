import uuid
from decimal import Decimal

from app.models.models import (
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    Shipment,
    User,
    UserStatus,
)


def make_order(db_session, user_id, *, deleted_at=None):
    order = Order(
        id=uuid.uuid4(),
        order_number=f"PP-{uuid.uuid4().hex[:12].upper()}",
        user_id=user_id,
        status=OrderStatus.SHIPPED,
        currency="INR",
        subtotal_amount=Decimal("499.00"),
        shipping_amount=Decimal("40.00"),
        tax_amount=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("539.00"),
        shipping_address_snapshot={"recipient_name": "Test Customer", "city": "Kashipur"},
        deleted_at=deleted_at,
    )
    db_session.add(order)
    db_session.flush()
    return order


def test_user_can_get_order_details_and_tracking(client, db_session, user_headers):
    user = db_session.query(User).filter_by(email="regular-test@example.com").one()
    order = make_order(db_session, user.id)
    db_session.add_all([
        OrderItem(
            id=uuid.uuid4(), order_id=order.id, variant_id=None,
            sku_snapshot="DOG-FOOD-1KG", name_snapshot="Chicken Dog Food",
            unit_price=Decimal("499.00"), quantity=1,
        ),
        Shipment(
            id=uuid.uuid4(), order_id=order.id, carrier="Test Courier",
            tracking_number="TRACK123", status="in_transit",
        ),
        OrderStatusHistory(
            id=uuid.uuid4(), order_id=order.id, old_status="processing",
            new_status="shipped", reason="Handed to carrier",
        ),
    ])
    db_session.flush()

    response = client.get(f"/api/v1/orders/{order.id}", headers=user_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(order.id)
    assert body["items"][0]["name_snapshot"] == "Chicken Dog Food"
    assert body["shipments"][0]["tracking_number"] == "TRACK123"
    assert body["status_history"][0]["new_status"] == "shipped"


def test_user_cannot_view_another_users_order(client, db_session, user_headers):
    other_email = f"other-{uuid.uuid4().hex[:8]}@example.com"
    other_user = User(
        id=uuid.uuid4(),
        email=other_email,
        email_normalized=other_email,
        display_name="Other User",
        status=UserStatus.ACTIVE,
    )
    db_session.add(other_user)
    db_session.flush()
    order = make_order(db_session, other_user.id)

    response = client.get(f"/api/v1/orders/{order.id}", headers=user_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found."


def test_user_gets_404_for_missing_order(client, user_headers):
    response = client.get(f"/api/v1/orders/{uuid.uuid4()}", headers=user_headers)
    assert response.status_code == 404


def test_user_gets_404_for_soft_deleted_order(client, db_session, user_headers):
    from datetime import datetime, timezone

    user = db_session.query(User).filter_by(email="regular-test@example.com").one()
    order = make_order(db_session, user.id, deleted_at=datetime.now(timezone.utc))

    response = client.get(f"/api/v1/orders/{order.id}", headers=user_headers)

    assert response.status_code == 404


def test_order_detail_excludes_soft_deleted_shipments(
    client, db_session, user_headers
):
    from datetime import datetime, timezone

    user = (
        db_session.query(User)
        .filter_by(email="regular-test@example.com")
        .one()
    )
    order = make_order(db_session, user.id)

    active_shipment = Shipment(
        id=uuid.uuid4(),
        order_id=order.id,
        carrier="Test Courier",
        tracking_number="ACTIVE-TRACK",
        status="in_transit",
    )

    deleted_shipment = Shipment(
        id=uuid.uuid4(),
        order_id=order.id,
        carrier="Deleted Courier",
        tracking_number="DELETED-TRACK",
        status="pending",
        deleted_at=datetime.now(timezone.utc),
    )

    db_session.add_all([active_shipment, deleted_shipment])
    db_session.commit()

    response = client.get(
        f"/api/v1/orders/{order.id}",
        headers=user_headers,
    )

    assert response.status_code == 200
    body = response.json()

    tracking_numbers = [
        shipment["tracking_number"]
        for shipment in body["shipments"]
    ]

    assert "ACTIVE-TRACK" in tracking_numbers
    assert "DELETED-TRACK" not in tracking_numbers
    assert len(tracking_numbers) == 1
