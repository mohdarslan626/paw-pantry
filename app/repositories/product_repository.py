
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.models import Product, ProductStatus, ProductVariant

def _with_active_variants(statement):
    return statement.options(
        selectinload(
            Product.variants.and_(
                ProductVariant.is_active.is_(True),
                ProductVariant.deleted_at.is_(None),
            )
        )
    )

def get_product_by_id(db: Session, product_id: UUID) -> Product | None:
    statement = select(Product).where(
        Product.id == product_id,
        Product.deleted_at.is_(None),
    )
    statement = _with_active_variants(statement)
    return db.scalar(statement)


def get_product_by_slug(db: Session, slug: str) -> Product | None:
    statement = select(Product).where(
        Product.slug == slug,
        Product.deleted_at.is_(None),
    )
    return db.scalar(statement)



def list_products(
    db: Session,
    *,
    published_only: bool = True,
    skip: int = 0,
    limit: int = 20,
    search: str | None = None,
    category_id: int | None = None,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> list[Product]:
    statement = select(Product).where(
        Product.deleted_at.is_(None)
    )

    if published_only:
        statement = statement.where(
            Product.status == ProductStatus.ACTIVE
        )

    if search:
        search_term = f"%{search.strip()}%"
        statement = statement.where(
            Product.name.ilike(search_term)
            | Product.short_description.ilike(search_term)
            | Product.description.ilike(search_term)
        )

    if category_id is not None:
        statement = statement.where(
            Product.category_id == category_id
        )

    sort_columns = {
        "name": Product.name,
        "created_at": Product.created_at,
    }
    sort_column = sort_columns[sort_by]

    if sort_order == "desc":
        sort_column = sort_column.desc()
    else:
        sort_column = sort_column.asc()

    statement = _with_active_variants(statement)
    statement = (
        statement
        .order_by(sort_column, Product.id)
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def create_product(db: Session, product_data: dict) -> Product:
    product = Product(**product_data)
    db.add(product)

    try:
        db.commit()
        db.refresh(product)
        return product
    except Exception:
        db.rollback()
        raise


def update_product(
    db: Session,
    product: Product,
    update_data: dict,
) -> Product:
    for field, value in update_data.items():
        setattr(product, field, value)

    try:
        db.commit()
        db.refresh(product)
        return product
    except Exception:
        db.rollback()
        raise


def soft_delete_product(db: Session, product: Product) -> None:
    from datetime import datetime, timezone

    product.deleted_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
