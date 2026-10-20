
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.models import Cart, CartItem
from app.repositories.cart_repository import (
    commit_changes,
    create_cart,
    get_active_variant,
    get_cart_by_user,
    get_cart_item,
    get_cart_item_by_variant,
    refresh_cart,
    restore_cart_item,
    save_cart_item,
)
from app.schemas.cart import (
    CartItemResponse,
    CartResponse,
)


def _get_or_create_cart(db: Session, user_id: UUID) -> Cart:
    cart = get_cart_by_user(db, user_id)

    if cart is not None:
        return cart

    cart = create_cart(db, user_id)
    commit_changes(db)

    return cart


def _build_cart_response(cart: Cart) -> CartResponse:
    response_items = []
    subtotal = Decimal("0.00")
    currency = None

    for item in cart.items:
        if item.deleted_at is not None:
            continue

        variant = item.variant

        # Do not include unavailable products in the cart response.
        if (
            variant is None
            or variant.deleted_at is not None
            or not variant.is_active
            or variant.product is None
            or variant.product.deleted_at is not None
        ):
            continue

        if currency is None:
            currency = variant.currency
        elif currency != variant.currency:
            raise ValueError(
                "Cart items must use the same currency."
            )

        unit_price = variant.price
        subtotal += unit_price * item.quantity

        response_items.append(
            CartItemResponse(
                id=item.id,
                variant_id=variant.id,
                quantity=item.quantity,
                unit_price=unit_price,
                currency=variant.currency,
                product_name=variant.product.name,
                variant_name=variant.variant_name,
                weight_grams=variant.weight_grams,
            )
        )

    return CartResponse(
        id=cart.id,
        items=response_items,
        subtotal=subtotal,
        currency=currency or "INR",
    )


def get_cart_service(
    db: Session,
    user_id: UUID,
) -> CartResponse:
    cart = _get_or_create_cart(db, user_id)

    # Reload relationships after creating a cart or changing its items.
    cart = refresh_cart(db, cart.id)

    if cart is None:
        raise ValueError("Unable to retrieve cart.")

    return _build_cart_response(cart)



def add_cart_item_service(
    db: Session,
    user_id: UUID,
    variant_id: UUID,
    quantity: int,
) -> CartResponse:
    if quantity < 1 or quantity > 100:
        raise ValueError(
            "Quantity must be between 1 and 100."
        )

    variant = get_active_variant(db, variant_id)

    if variant is None:
        raise ValueError("Product variant is unavailable.")

    cart = _get_or_create_cart(db, user_id)

    existing_item = get_cart_item_by_variant(
        db,
        cart.id,
        variant_id,
    )

    if existing_item is not None:
        if existing_item.deleted_at is not None:
            restore_cart_item(existing_item, quantity)
        else:
            new_quantity = existing_item.quantity + quantity

            if new_quantity > 100:
                raise ValueError(
                    "Cart quantity cannot exceed 100 per variant."
                )

            existing_item.quantity = new_quantity
    else:
        save_cart_item(
            db,
            cart.id,
            variant_id,
            quantity,
        )

    commit_changes(db)

    return get_cart_service(db, user_id)


def update_cart_item_service(
    db: Session,
    user_id: UUID,
    item_id: UUID,
    quantity: int,
) -> CartResponse:
    cart = get_cart_by_user(db, user_id)

    if cart is None:
        raise ValueError("Cart item not found.")

    item = get_cart_item(db, cart.id, item_id)

    if item is None:
        raise ValueError("Cart item not found.")

    variant = get_active_variant(db, item.variant_id)

    if variant is None:
        raise ValueError(
            "Product variant is unavailable."
        )

    if quantity < 1 or quantity > 100:
        raise ValueError(
            "Quantity must be between 1 and 100."
        )

    item.quantity = quantity
    commit_changes(db)

    return get_cart_service(db, user_id)


def remove_cart_item_service(
    db: Session,
    user_id: UUID,
    item_id: UUID,
) -> CartResponse:
    cart = get_cart_by_user(db, user_id)

    if cart is None:
        raise ValueError("Cart item not found.")

    item = get_cart_item(db, cart.id, item_id)

    if item is None:
        raise ValueError("Cart item not found.")

    item.deleted_at = datetime.now(timezone.utc)
    item.deleted_by = user_id

    commit_changes(db)

    return get_cart_service(db, user_id)
