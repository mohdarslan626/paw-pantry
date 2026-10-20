
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Brand
from app.schemas.brand import BrandCreate
from datetime import datetime, timezone

def get_all_brands(db: Session) -> list[Brand]:
    statement = (
        select(Brand)
        .where(Brand.deleted_at.is_(None))
        .order_by(Brand.name.asc())
    )
    return list(db.scalars(statement).all())


def create_brand(db: Session, brand_data: BrandCreate) -> Brand:
    brand = Brand(**brand_data.model_dump())

    try:
        db.add(brand)
        db.commit()
        db.refresh(brand)
        return brand
    except Exception:
        db.rollback()
        raise


def get_brand_by_id(db: Session, brand_id: int) -> Brand | None:
    statement = select(Brand).where(
        Brand.id == brand_id,
        Brand.deleted_at.is_(None),
    )
    return db.scalar(statement)


def update_brand(
    db: Session,
    brand: Brand,
    update_data: dict,
) -> Brand:
    try:
        for field, value in update_data.items():
            setattr(brand, field, value)

        db.commit()
        db.refresh(brand)
        return brand
    except Exception:
        db.rollback()
        raise

def soft_delete_brand(db: Session, brand: Brand) -> None:
    try:
        brand.deleted_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()
        raise
    