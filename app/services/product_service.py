
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.models import Brand, Category, Product, ProductStatus
from app.repositories.product_repository import (
    create_product,
    get_product_by_id,
    get_product_by_slug,
    list_products,
    soft_delete_product,
    update_product,
)
from app.schemas.product import ProductCreate, ProductUpdate



def list_products_service(
    db: Session,
    *,
    include_drafts: bool = False,
    skip: int = 0,
    limit: int = 20,
    search: str | None = None,
    category_id: int | None = None,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> list[Product]:
    return list_products(
        db,
        published_only=not include_drafts,
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )


def get_product_service(
    db: Session,
    product_id: UUID,
    *,
    include_drafts: bool = False,
) -> Product | None:
    product = get_product_by_id(db, product_id)

    if product is None:
        return None

    if not include_drafts and product.status != ProductStatus.ACTIVE:
        return None

    return product


def create_product_service(
    db: Session,
    product_data: ProductCreate,
) -> Product:
    data = product_data.model_dump()

    if get_product_by_slug(db, data["slug"]):
        raise ValueError("A product with this slug already exists.")

    if db.get(Category, data["category_id"]) is None:
        raise ValueError("The selected category does not exist.")

    if data["brand_id"] is not None:
        brand = db.get(Brand, data["brand_id"])
        if brand is None or brand.deleted_at is not None:
            raise ValueError("The selected brand does not exist.")

    return create_product(db, data)


def update_product_service(
    db: Session,
    product_id: UUID,
    update_data: ProductUpdate,
) -> Product | None:
    product = get_product_by_id(db, product_id)

    if product is None:
        return None

    data = update_data.model_dump(exclude_unset=True)

    if "slug" in data and data["slug"] != product.slug:
        if get_product_by_slug(db, data["slug"]):
            raise ValueError("A product with this slug already exists.")

    if "category_id" in data and data["category_id"] is not None:
        if db.get(Category, data["category_id"]) is None:
            raise ValueError("The selected category does not exist.")

    if "brand_id" in data and data["brand_id"] is not None:
        brand = db.get(Brand, data["brand_id"])
        if brand is None or brand.deleted_at is not None:
            raise ValueError("The selected brand does not exist.")

    if data.get("status") == ProductStatus.ACTIVE:
        if product.published_at is None:
            data["published_at"] = datetime.now(timezone.utc)
    elif data.get("status") == ProductStatus.DRAFT:
        data["published_at"] = None

    return update_product(db, product, data)


def delete_product_service(db: Session, product_id: UUID) -> bool:
    product = get_product_by_id(db, product_id)

    if product is None:
        return False

    soft_delete_product(db, product)
    return True
