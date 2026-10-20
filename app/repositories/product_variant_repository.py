
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Product, ProductVariant


def get_product_for_variant(
    db: Session,
    product_id: UUID,
) -> Product | None:
    statement = select(Product).where(
        Product.id == product_id,
        Product.deleted_at.is_(None),
    )
    return db.scalar(statement)


def get_variant_by_id(
    db: Session,
    variant_id: UUID,
) -> ProductVariant | None:
    statement = select(ProductVariant).where(
        ProductVariant.id == variant_id,
        ProductVariant.deleted_at.is_(None),
    )
    return db.scalar(statement)


def list_product_variants(
    db: Session,
    product_id: UUID,
) -> list[ProductVariant]:
    statement = (
        select(ProductVariant)
        .where(
            ProductVariant.product_id == product_id,
            ProductVariant.deleted_at.is_(None),
        )
        .order_by(ProductVariant.weight_grams, ProductVariant.variant_name)
    )
    return list(db.scalars(statement).all())


def create_product_variant(
    db: Session,
    product_id: UUID,
    variant_data: dict,
) -> ProductVariant:
    variant = ProductVariant(
        product_id=product_id,
        **variant_data,
    )
    db.add(variant)

    try:
        db.commit()
        db.refresh(variant)
        return variant
    except Exception:
        db.rollback()
        raise


def update_product_variant(
    db: Session,
    variant: ProductVariant,
    update_data: dict,
) -> ProductVariant:
    for field, value in update_data.items():
        setattr(variant, field, value)

    try:
        db.commit()
        db.refresh(variant)
        return variant
    except Exception:
        db.rollback()
        raise


def soft_delete_product_variant(
    db: Session,
    variant: ProductVariant,
) -> None:
    from datetime import datetime, timezone

    variant.deleted_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
