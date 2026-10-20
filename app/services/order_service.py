
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import secrets
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import (
    CartItem,
    IdempotencyKey,
    InventoryMovement,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    ProductStatus,
    ProductVariant,
)
from app.repositories.order_repository import (
    get_checkout_cart,
    get_shipping_address,
    lock_inventory,
)
from app.schemas.order import CheckoutRequest, CheckoutResponse


def checkout_service(
    db: Session,
    user_id: UUID,
    request: CheckoutRequest,
) -> CheckoutResponse:
    scope = f"checkout:{user_id}"

    # Hash the request so the same key cannot be reused
    # with a different shipping address.
    request_hash = sha256(
        json.dumps(
            {"shipping_address_id": str(request.shipping_address_id)},
            sort_keys=True,
        ).encode()
    ).hexdigest()

    try:
        # Serialize checkout requests for this customer/key.
        key_record = db.scalar(
            select(IdempotencyKey)
            .where(
                IdempotencyKey.scope == scope,
                IdempotencyKey.key == request.idempotency_key,
            )
            .with_for_update()
        )

        if key_record is not None:
            if key_record.request_hash != request_hash:
                raise ValueError(
                    "Idempotency key was already used with different checkout details."
                )

            if key_record.response_reference:
                existing_order = db.get(
                    Order, UUID(key_record.response_reference)
                )
                if existing_order is not None:
                    return _order_response(db, existing_order)

        else:
            key_record = IdempotencyKey(
                scope=scope,
                key=request.idempotency_key,
                request_hash=request_hash,
            )
            db.add(key_record)
            db.flush()

        address = get_shipping_address(
            db, user_id, request.shipping_address_id
        )
        if address is None:
            raise ValueError(
                "Shipping address not found for this customer."
            )

        cart = get_checkout_cart(db, user_id)
        if cart is None:
            raise ValueError("Your cart is empty.")

        cart_items = [
            item for item in cart.items
            if item.deleted_at is None
        ]
        if not cart_items:
            raise ValueError("Your cart is empty.")

        # Lock inventory in a stable order to reduce deadlocks.
        variant_ids = sorted(
            {item.variant_id for item in cart_items},
            key=str,
        )
        inventory_by_variant = {}
        for variant_id in variant_ids:
            inventory_by_variant[variant_id] = lock_inventory(
                db, variant_id
            )

        # Reload current variant/product data after acquiring locks.
        subtotal = Decimal("0.00")
        order_lines = []
        currency = None

        for item in cart_items:
            variant = db.scalar(
                select(ProductVariant)
                .where(
                    ProductVariant.id == item.variant_id,
                    ProductVariant.deleted_at.is_(None),
                    ProductVariant.is_active.is_(True),
                )
                .with_for_update()
            )

            if (
                variant is None
                or variant.product is None
                or variant.product.deleted_at is not None
                or variant.product.status != ProductStatus.ACTIVE
            ):
                raise ValueError(
                    "A product in your cart is no longer available."
                )

            if currency is None:
                currency = variant.currency
            elif currency != variant.currency:
                raise ValueError(
                    "Cart items must use the same currency."
                )

            locations = inventory_by_variant[item.variant_id]
            available = sum(
                inventory.on_hand - inventory.reserved
                for inventory in locations
            )

            if available < item.quantity:
                raise ValueError(
                    f"Insufficient stock for {variant.variant_name}."
                )

            subtotal += variant.price * item.quantity
            order_lines.append((item, variant, locations))

        if currency is None:
            currency = "INR"

        # Shipping/tax/discount rules are not yet configured.
        shipping = Decimal("0.00")
        tax = Decimal("0.00")
        discount = Decimal("0.00")
        total = subtotal + shipping + tax - discount

        address_snapshot = {
            "recipient_name": address.recipient_name,
            "phone": address.phone,
            "line1": address.line1,
            "line2": address.line2,
            "city": address.city,
            "state_region": address.state_region,
            "postal_code": address.postal_code,
            "country_code": address.country_code,
        }

        order = Order(
            order_number=f"PP-{secrets.token_hex(8).upper()}",
            user_id=user_id,
            status=OrderStatus.PENDING,
            currency=currency,
            subtotal_amount=subtotal,
            shipping_amount=shipping,
            tax_amount=tax,
            discount_amount=discount,
            total_amount=total,
            shipping_address_snapshot=address_snapshot,
            customer_email_snapshot=None,
        )
        db.add(order)
        db.flush()

        for item, variant, locations in order_lines:
            remaining = item.quantity

            # Reserve available units across locations.
            for inventory in locations:
                available_here = inventory.on_hand - inventory.reserved
                reserve_quantity = min(remaining, available_here)

                if reserve_quantity <= 0:
                    continue

                inventory.reserved += reserve_quantity
                db.add(
                    InventoryMovement(
                        variant_id=variant.id,
                        location_id=inventory.location_id,
                        quantity_delta=-reserve_quantity,
                        reason="order_reservation",
                        reference_type="order",
                        reference_id=order.id,
                    )
                )
                remaining -= reserve_quantity

                if remaining == 0:
                    break

            if remaining > 0:
                raise ValueError(
                    f"Insufficient stock for {variant.variant_name}."
                )

            db.add(
                OrderItem(
                    order_id=order.id,
                    variant_id=variant.id,
                    sku_snapshot=variant.sku,
                    name_snapshot=(
                        f"{variant.product.name} - {variant.variant_name}"
                    ),
                    unit_price=variant.price,
                    quantity=item.quantity,
                    product_snapshot={
                        "product_name": variant.product.name,
                        "variant_name": variant.variant_name,
                        "weight_grams": variant.weight_grams,
                        "currency": variant.currency,
                    },
                )
            )

            # Soft-delete purchased cart item.
            item.deleted_at = datetime.now(timezone.utc)
            item.deleted_by = user_id

        db.add(
            OrderStatusHistory(
                order_id=order.id,
                old_status=None,
                new_status=OrderStatus.PENDING.value,
                reason="Order created at checkout.",
            )
        )

        key_record.response_reference = str(order.id)
        db.flush()

        response = _order_response(db, order)
        db.commit()
        return response

    except Exception:
        db.rollback()
        raise


def _order_response(
    db: Session,
    order: Order,
) -> CheckoutResponse:
    db.refresh(order)
    return CheckoutResponse(
        id=order.id,
        order_number=order.order_number,
        status=order.status.value,
        currency=order.currency,
        subtotal_amount=order.subtotal_amount,
        shipping_amount=order.shipping_amount,
        tax_amount=order.tax_amount,
        discount_amount=order.discount_amount,
        total_amount=order.total_amount,
        shipping_address_snapshot=order.shipping_address_snapshot,
        items=[
            {
                "id": item.id,
                "variant_id": item.variant_id,
                "sku_snapshot": item.sku_snapshot,
                "name_snapshot": item.name_snapshot,
                "unit_price": item.unit_price,
                "quantity": item.quantity,
            }
            for item in db.scalars(
                select(OrderItem).where(
                    OrderItem.order_id == order.id,
                    OrderItem.deleted_at.is_(None),
                )
            ).all()
        ],
    )
