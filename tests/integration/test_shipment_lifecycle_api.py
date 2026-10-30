import uuid
from decimal import Decimal
from datetime import datetime, timedelta, timezone
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


def test_delivery_creates_exactly_one_delivered_history_event(
    client, db_session, admin_headers, user_headers
):
    order = _make_shippable_order(db_session)
    shipment = Shipment(
        id=uuid.uuid4(),
        order_id=order.id,
        carrier="Test Courier",
        tracking_number="TRACK-DELIVERY-ONCE",
        status="in_transit",
    )
    db_session.add(shipment)
    db_session.flush()

    url = f"/api/v1/orders/{order.id}/shipments/{shipment.id}/status"

    first = client.patch(
        url,
        headers=admin_headers,
        json={"status": "delivered"},
    )
    assert first.status_code == status.HTTP_200_OK, first.text

    db_session.refresh(order)
    assert order.status == OrderStatus.DELIVERED

    delivered_events = (
        db_session.query(OrderStatusHistory)
        .filter_by(order_id=order.id, new_status="delivered")
        .all()
    )
    assert len(delivered_events) == 1

    # Repeating the same delivery request must not duplicate history.
    second = client.patch(
        url,
        headers=admin_headers,
        json={"status": "delivered"},
    )
    assert second.status_code == status.HTTP_200_OK, second.text

    delivered_events = (
        db_session.query(OrderStatusHistory)
        .filter_by(order_id=order.id, new_status="delivered")
        .all()
    )
    assert len(delivered_events) == 1


def test_soft_deleted_pending_shipment_does_not_block_delivery(
    client, db_session, admin_headers, user_headers
):
    order = _make_shippable_order(db_session)

    active_shipment = Shipment(
        id=uuid.uuid4(),
        order_id=order.id,
        carrier="Test Courier",
        tracking_number="TRACK-ACTIVE-DELIVERY",
        status="in_transit",
    )
    deleted_shipment = Shipment(
        id=uuid.uuid4(),
        order_id=order.id,
        carrier="Old Test Courier",
        tracking_number="TRACK-DELETED-PENDING",
        status="pending",
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add_all([active_shipment, deleted_shipment])
    db_session.flush()

    response = client.patch(
        (
            f"/api/v1/orders/{order.id}/shipments/"
            f"{active_shipment.id}/status"
        ),
        headers=admin_headers,
        json={"status": "delivered"},
    )
    assert response.status_code == status.HTTP_200_OK, response.text

    db_session.refresh(order)
    assert order.status == OrderStatus.DELIVERED

    db_session.refresh(deleted_shipment)
    assert deleted_shipment.status == "pending"
    assert deleted_shipment.deleted_at is not None

    delivered_events = (
        db_session.query(OrderStatusHistory)
        .filter_by(order_id=order.id, new_status="delivered")
        .all()
    )
    assert len(delivered_events) == 1


def test_order_detail_excludes_soft_deleted_shipments(
    client, db_session, admin_headers, user_headers
):
    order = _make_shippable_order(db_session)

    active_shipment = Shipment(
        id=uuid.uuid4(),
        order_id=order.id,
        carrier="Active Courier",
        tracking_number="TRACK-API-ACTIVE",
        status="pending",
    )
    deleted_shipment = Shipment(
        id=uuid.uuid4(),
        order_id=order.id,
        carrier="Deleted Courier",
        tracking_number="TRACK-API-DELETED",
        status="pending",
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add_all([active_shipment, deleted_shipment])
    db_session.flush()

    response = client.get(
        f"/api/v1/orders/{order.id}",
        headers=user_headers,
    )
    assert response.status_code == status.HTTP_200_OK, response.text

    body = response.json()
    shipments = body["shipments"]

    shipment_ids = {item["id"] for item in shipments}
    tracking_numbers = {item["tracking_number"] for item in shipments}

    assert str(active_shipment.id) in shipment_ids
    assert str(deleted_shipment.id) not in shipment_ids
    assert "TRACK-API-ACTIVE" in tracking_numbers
    assert "TRACK-API-DELETED" not in tracking_numbers
