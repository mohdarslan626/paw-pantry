
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.models import (
    Cart,
    CartItem,
    Product,
    ProductStatus,
    ProductVariant,
)


def _with_cart_details(statement):
    """Load only active cart items and their associated product details."""
    return statement.options(
        selectinload(
            Cart.items.and_(CartItem.deleted_at.is_(None))
        )
        .selectinload(CartItem.variant)
        .selectinload(ProductVariant.product)
    )


def get_cart_by_user(db: Session, user_id: UUID) -> Cart | None:
    statement = (
        select(Cart)
        .where(
            Cart.user_id == user_id,
            Cart.deleted_at.is_(None),
        )
        .order_by(Cart.created_at.desc(), Cart.id)
    )
    statement = _with_cart_details(statement)
    return db.scalars(statement).first()


def get_cart_item(
    db: Session,
    cart_id: UUID,
    item_id: UUID,
) -> CartItem | None:
    statement = select(CartItem).where(
        CartItem.id == item_id,
        CartItem.cart_id == cart_id,
        CartItem.deleted_at.is_(None),
    )
    return db.scalar(statement)


def get_active_variant(
    db: Session,
    variant_id: UUID,
) -> ProductVariant | None:
    statement = (
        select(ProductVariant)
        .join(Product, Product.id == ProductVariant.product_id)
        .where(
            ProductVariant.id == variant_id,
            ProductVariant.deleted_at.is_(None),
            ProductVariant.is_active.is_(True),
            Product.deleted_at.is_(None),
            Product.status == ProductStatus.ACTIVE,
        )
    )
    return db.scalar(statement)


def get_cart_item_by_variant(
    db: Session,
    cart_id: UUID,
    variant_id: UUID,
) -> CartItem | None:
    """Find an item whether active or soft-deleted.

    Prefer an active row so adding an existing variant updates its quantity.
    """
    statement = (
        select(CartItem)
        .where(
            CartItem.cart_id == cart_id,
            CartItem.variant_id == variant_id,
        )
        .order_by(
            CartItem.deleted_at.is_(None).desc(),
            CartItem.created_at.desc(),
        )
    )
    return db.scalars(statement).first()


def create_cart(db: Session, user_id: UUID) -> Cart:
    cart = Cart(user_id=user_id)
    db.add(cart)
    db.flush()
    return cart


def save_cart_item(
    db: Session,
    cart_id: UUID,
    variant_id: UUID,
    quantity: int,
) -> CartItem:
    item = CartItem(
        cart_id=cart_id,
        variant_id=variant_id,
        quantity=quantity,
    )
    db.add(item)
    db.flush()
    return item


def restore_cart_item(
    item: CartItem,
    quantity: int,
) -> CartItem:
    """Restore a soft-deleted item instead of inserting a duplicate row."""
    item.quantity = quantity
    item.deleted_at = None
    item.deleted_by = None
    return item


def commit_changes(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def refresh_cart(db: Session, cart_id: UUID) -> Cart | None:
    """Reload the cart and its active items after a database change."""
    db.expire_all()

    statement = select(Cart).where(
        Cart.id == cart_id,
        Cart.deleted_at.is_(None),
    )
    statement = _with_cart_details(statement)

    return db.scalar(statement)
