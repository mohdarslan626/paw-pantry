
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.models import User, Order
from app.schemas.order import (
    CheckoutRequest, CheckoutResponse, OrderDetailResponse, OrderHistoryResponse,
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
        )
    )
    order = db.scalars(statement).first()
    if order is None:
        # Use the same response for missing and other users' orders to avoid
        # disclosing whether another customer's order exists.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    order.shipments.sort(key=lambda shipment: shipment.created_at)
    order.status_history.sort(key=lambda event: event.created_at)
    return order
