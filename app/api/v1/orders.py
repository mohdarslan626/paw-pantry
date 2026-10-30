from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload, with_loader_criteria

from app.core.dependencies import get_current_user, require_admin
from app.db.session import get_db
from app.models.models import (
    Order,
    OrderStatus,
    OrderStatusHistory,
    Shipment,
    User,
)
from app.schemas.order import (
    CheckoutRequest,
    CheckoutResponse,
    OrderDetailResponse,
    OrderHistoryResponse,
    ShipmentCreateRequest,
    ShipmentStatusUpdateRequest,
    ShipmentTrackingResponse,
)
from app.services.order_service import checkout_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
def checkout(
    request: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return checkout_service(
            db=db,
            user_id=current_user.id,
            request=request,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "address not found" in message.lower()
            else status.HTTP_409_CONFLICT
            if "insufficient stock" in message.lower()
            or "idempotency key" in message.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail=message,
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Checkout conflicted with another request. Please retry.",
        ) from exc


@router.get("/", response_model=list[OrderHistoryResponse])
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Order)
        .where(
            Order.user_id == current_user.id,
            Order.deleted_at.is_(None),
        )
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
    )
    return db.scalars(statement).all()


@router.get("/{order_id}", response_model=OrderDetailResponse)
def get_my_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return details and tracking information for the current user's order."""
    statement = (
        select(Order)
        .where(
            Order.id == order_id,
            Order.user_id == current_user.id,
            Order.deleted_at.is_(None),
        )
        .options(
            selectinload(Order.items),
            selectinload(Order.shipments),
            selectinload(Order.status_history),
            with_loader_criteria(
                Shipment,
                Shipment.deleted_at.is_(None),
            ),
        )
    )
    order = db.scalars(statement).first()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    order.shipments.sort(key=lambda shipment: shipment.created_at)
    order.status_history.sort(key=lambda event: event.created_at)
    return order


@router.post(
    "/{order_id}/shipments",
    response_model=ShipmentTrackingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_shipment(
    order_id: UUID,
    request: ShipmentCreateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Create a pending shipment for an order. Admin access is required."""
    order = db.scalars(
        select(Order)
        .where(Order.id == order_id, Order.deleted_at.is_(None))
        .with_for_update()
    ).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")

    if order.status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED, OrderStatus.DELIVERED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot create a shipment for an order with status '{order.status.value}'.",
        )
    
    """Create a check for an order already having a shipment with the same tracking number and carrier."""
    existing_shipment = db.scalars(
    select(Shipment).where(
        Shipment.order_id == order.id,
        Shipment.tracking_number == request.tracking_number,
        Shipment.deleted_at.is_(None),
    )
    ).first()

    if existing_shipment is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A shipment with this tracking number already exists for this order.",
        )

    shipment = Shipment(
        order_id=order.id,
        carrier=request.carrier,
        tracking_number=request.tracking_number,
        status="pending",
    )
    db.add(shipment)
    try:
        db.commit()
        db.refresh(shipment)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shipment could not be created due to a data conflict.",
        ) from exc
    return shipment

def reconcile_order_delivery_status(db: Session, order: Order) -> bool:
    """Mark an order delivered when all its active shipments are delivered."""
    if order.status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED):
        return False

    db.flush()

    active_shipments = db.scalars(
        select(Shipment).where(
            Shipment.order_id == order.id,
            Shipment.deleted_at.is_(None),
        )
    ).all()

    # Do not treat an order with zero active shipments as delivered.
    if not active_shipments:
        return False

    if not all(shipment.status == "delivered" for shipment in active_shipments):
        return False

    if order.status == OrderStatus.DELIVERED:
        return False

    old_status = order.status
    order.status = OrderStatus.DELIVERED

    db.add(
        OrderStatusHistory(
            order_id=order.id,
            old_status=old_status.value,
            new_status=OrderStatus.DELIVERED.value,
            reason="All active shipments for the order have been delivered.",
        )
    )
    return True

@router.patch(
    "/{order_id}/shipments/{shipment_id}/status",
    response_model=ShipmentTrackingResponse,
)

def update_shipment_status(
    order_id: UUID,
    shipment_id: UUID,
    request: ShipmentStatusUpdateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Advance a shipment through pending -> in_transit -> delivered."""
    order = db.scalars(
        select(Order)
        .where(Order.id == order_id, Order.deleted_at.is_(None))
        .with_for_update()
    ).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")

    shipment = db.scalars(
        select(Shipment)
        .where(
            Shipment.id == shipment_id, 
            Shipment.order_id == order_id, 
            Shipment.deleted_at.is_(None),
        )
        .with_for_update()
    ).first()
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found.")

    target = request.status
    current = shipment.status
    allowed = {"pending": {"in_transit"}, "in_transit": {"delivered"}, "delivered": set()}

    # A repeated request is safe to retry and does not create duplicate history.
    if target == current:
        if (
            target == "delivered"
            and reconcile_order_delivery_status(db, order)
        ):
            try:
                db.commit()
                db.refresh(shipment)
            except IntegrityError as exc:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Shipment status update conflicted with another request.",
                ) from exc
        return shipment

    if target not in allowed.get(current, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid shipment transition: '{current}' -> '{target}'.",
        )

    if order.status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot update a shipment for an order with status '{order.status.value}'.",
        )

    if target == "in_transit" and order.status == OrderStatus.DELIVERED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot move a shipment back to transit after the order is delivered.",
        )

    now = datetime.now(timezone.utc)
    shipment.status = target
    if target == "in_transit":
        shipment.shipped_at = now
        if order.status != OrderStatus.SHIPPED:
            old_status = order.status
            order.status = OrderStatus.SHIPPED
            db.add(
                OrderStatusHistory(
                    order_id=order.id,
                    old_status=old_status.value,
                    new_status=OrderStatus.SHIPPED.value,
                    reason="Shipment handed to carrier.",
                )
            )
    elif target == "delivered":
        shipment.delivered_at = now
        reconcile_order_delivery_status(db, order)
    try:
        db.commit()
        db.refresh(shipment)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shipment status update conflicted with another request.",
        ) from exc
    return shipment
