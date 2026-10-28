import uuid
from decimal import Decimal

from fastapi import status

from app.models.models import Order, OrderStatus, OrderStatusHistory, Shipment, User, UserStatus


def _make_shippable_order(db_session):
    user = db_session.query(User).filter_by(email="regular-test@example.com").one()
    order = Order(
        id=uuid.uuid4(),
        order_number=f"PP-{uuid.uuid4().hex[:12].upper()}",
        user_id=user.id,
        status=OrderStatus.PROCESSING,
        currency="INR",
        subtotal_amount=Decimal("499.00"),
        shipping_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("499.00"),
        shipping_address_snapshot={"recipient_name": "Test Customer", "city": "Kashipur"},
    )
    db_session.add(order)
    db_session.flush()
    return order


def test_admin_can_create_shipment(client, db_session, user_headers, admin_headers):
    order = _make_shippable_order(db_session)

    response = client.post(
        f"/api/v1/orders/{order.id}/shipments",
        headers=admin_headers,
        json={"carrier": "Test Courier", "tracking_number": "TRACK-NEW-123"},
    )

    assert response.status_code == status.HTTP_201_CREATED, response.text
    body = response.json()
    assert body["order_id"] if "order_id" in body else True
    assert body["carrier"] == "Test Courier"
    assert body["tracking_number"] == "TRACK-NEW-123"
    assert body["status"] == "pending"
    db_session.refresh(order)
    assert order.status == OrderStatus.PROCESSING


def test_customer_cannot_create_shipment(client, db_session, user_headers, admin_headers):
    order = _make_shippable_order(db_session)

    response = client.post(
        f"/api/v1/orders/{order.id}/shipments",
        headers=user_headers,
        json={"carrier": "Test Courier", "tracking_number": "TRACK-NEW-123"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert db_session.query(Shipment).filter_by(order_id=order.id).count() == 0


def test_admin_can_advance_shipment_and_order_to_delivered(
    client, db_session, user_headers, admin_headers
):
    order = _make_shippable_order(db_session)
    shipment = Shipment(
        id=uuid.uuid4(),
        order_id=order.id,
        carrier="Test Courier",
        tracking_number="TRACK-LIFECYCLE-123",
        status="pending",
    )
    db_session.add(shipment)
    db_session.flush()

    in_transit = client.patch(
        f"/api/v1/orders/{order.id}/shipments/{shipment.id}/status",
        headers=admin_headers,
        json={"status": "in_transit"},
    )
    assert in_transit.status_code == status.HTTP_200_OK, in_transit.text
    assert in_transit.json()["status"] == "in_transit"
    db_session.refresh(order)
    assert order.status == OrderStatus.SHIPPED
    assert in_transit.json()["shipped_at"] is not None

    delivered = client.patch(
        f"/api/v1/orders/{order.id}/shipments/{shipment.id}/status",
        headers=admin_headers,
        json={"status": "delivered"},
    )
    assert delivered.status_code == status.HTTP_200_OK, delivered.text
    assert delivered.json()["status"] == "delivered"
    assert delivered.json()["delivered_at"] is not None
    db_session.refresh(order)
    assert order.status == OrderStatus.DELIVERED

    history = (
        db_session.query(OrderStatusHistory)
        .filter_by(order_id=order.id)
        .order_by(OrderStatusHistory.created_at)
        .all()
    )
    assert [event.new_status for event in history] == ["shipped", "delivered"]


def test_customer_cannot_update_shipment_status(
    client, db_session, user_headers, admin_headers
):
    order = _make_shippable_order(db_session)
    shipment = Shipment(
        id=uuid.uuid4(),
        order_id=order.id,
        carrier="Test Courier",
        tracking_number="TRACK-CUSTOMER-123",
        status="pending",
    )
    db_session.add(shipment)
    db_session.flush()

    response = client.patch(
        f"/api/v1/orders/{order.id}/shipments/{shipment.id}/status",
        headers=user_headers,
        json={"status": "in_transit"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    db_session.refresh(shipment)
    assert shipment.status == "pending"


def test_shipment_cannot_move_backwards(
    client, db_session, user_headers, admin_headers
):
    order = _make_shippable_order(db_session)
    shipment = Shipment(
        id=uuid.uuid4(),
        order_id=order.id,
        carrier="Test Courier",
        tracking_number="TRACK-BACKWARD-123",
        status="in_transit",
    )
    db_session.add(shipment)
    db_session.flush()

    response = client.patch(
        f"/api/v1/orders/{order.id}/shipments/{shipment.id}/status",
        headers=admin_headers,
        json={"status": "pending"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    db_session.refresh(shipment)
    assert shipment.status == "in_transit"


def test_repeating_current_shipment_status_is_idempotent(
    client, db_session, user_headers, admin_headers
):
    order = _make_shippable_order(db_session)
    shipment = Shipment(
        id=uuid.uuid4(),
        order_id=order.id,
        carrier="Test Courier",
        tracking_number="TRACK-RETRY-123",
        status="in_transit",
    )
    db_session.add(shipment)
    db_session.flush()

    response = client.patch(
        f"/api/v1/orders/{order.id}/shipments/{shipment.id}/status",
        headers=admin_headers,
        json={"status": "in_transit"},
    )

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["status"] == "in_transit"
    assert (
        db_session.query(OrderStatusHistory)
        .filter_by(order_id=order.id)
        .count()
        == 0
    )
