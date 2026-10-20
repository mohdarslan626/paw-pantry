
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Brand
from app.repositories.brand_repository import (create_brand, get_all_brands, get_brand_by_id, update_brand, soft_delete_brand)
from app.schemas.brand import BrandCreate, BrandUpdate


def list_brands(db: Session) -> list[Brand]:
    return get_all_brands(db)


def create_brand_service(db: Session, brand_data: BrandCreate) -> Brand:
    existing_brand = db.scalar(
        select(Brand).where(
            Brand.slug == brand_data.slug,
            Brand.deleted_at.is_(None),
        )
    )

    if existing_brand is not None:
        raise ValueError("A brand with this slug already exists.")

    return create_brand(db, brand_data)


def get_brand_service(db: Session, brand_id: int) -> Brand:
    brand = get_brand_by_id(db, brand_id)

    if brand is None:
        raise ValueError("Brand not found.")

    return brand


def update_brand_service(
    db: Session,
    brand_id: int,
    update_data: BrandUpdate,
) -> Brand:
    brand = get_brand_by_id(db, brand_id)

    if brand is None:
        raise ValueError("Brand not found.")

    changes = update_data.model_dump(exclude_unset=True)

    # The database requires these fields to remain non-null.
    for required_field in ("name", "slug"):
        if required_field in changes and changes[required_field] is None:
            raise ValueError(f"{required_field} cannot be null.")

    if "slug" in changes:
        existing_brand = db.scalar(
            select(Brand).where(
                Brand.slug == changes["slug"],
                Brand.id != brand_id,
                Brand.deleted_at.is_(None),
            )
        )
        if existing_brand is not None:
            raise ValueError("A brand with this slug already exists.")

    return update_brand(db, brand, changes)

def delete_brand_service(db: Session, brand_id: int) -> None:
    brand = get_brand_by_id(db, brand_id)

    if brand is None:
        raise ValueError("Brand not found.")

    soft_delete_brand(db, brand)