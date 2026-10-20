
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.models import (
    Cart,
    CartItem,
    Inventory,
    Product,
    ProductVariant,
    UserAddress,
)


def get_shipping_address(
    db: Session,
    user_id: UUID,
    address_id: UUID,
) -> UserAddress | None:
    statement = select(UserAddress).where(
        UserAddress.id == address_id,
        UserAddress.user_id == user_id,
        UserAddress.address_type == "shipping",
        UserAddress.deleted_at.is_(None),
    )
    return db.scalar(statement)


def get_checkout_cart(db: Session, user_id: UUID) -> Cart | None:
    statement = (
        select(Cart)
        .where(
            Cart.user_id == user_id,
            Cart.deleted_at.is_(None),
        )
        .order_by(Cart.created_at.desc(), Cart.id)
        .options(
            selectinload(
                Cart.items.and_(CartItem.deleted_at.is_(None))
            )
            .selectinload(CartItem.variant)
            .selectinload(ProductVariant.product)
        )
    )
    return db.scalars(statement).first()


def lock_inventory(
    db: Session,
    variant_id: UUID,
) -> list[Inventory]:
    statement = (
        select(Inventory)
        .where(
            Inventory.variant_id == variant_id,
            Inventory.deleted_at.is_(None),
        )
        .order_by(Inventory.location_id)
        .with_for_update()
    )
    return list(db.scalars(statement).all())
