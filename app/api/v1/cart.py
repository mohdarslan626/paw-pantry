
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.models import User
from app.schemas.cart import (
    CartItemCreate,
    CartItemUpdate,
    CartResponse,
)
from app.services.cart_service import (
    add_cart_item_service,
    get_cart_service,
    remove_cart_item_service,
    update_cart_item_service,
)

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("/", response_model=CartResponse)
def get_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CartResponse:
    try:
        return get_cart_service(db, current_user.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/items", response_model=CartResponse)
def add_cart_item(
    item_data: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CartResponse:
    try:
        return add_cart_item_service(
            db,
            current_user.id,
            item_data.variant_id,
            item_data.quantity,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The cart item conflicts with an existing record.",
        ) from exc


@router.patch("/items/{item_id}", response_model=CartResponse)
def update_cart_item(
    item_id: UUID,
    item_data: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CartResponse:
    try:
        return update_cart_item_service(
            db,
            current_user.id,
            item_id,
            item_data.quantity,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND
            if str(exc) == "Cart item not found."
            else status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete("/items/{item_id}", response_model=CartResponse)
def remove_cart_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CartResponse:
    try:
        return remove_cart_item_service(
            db,
            current_user.id,
            item_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND
            if str(exc) == "Cart item not found."
            else status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
