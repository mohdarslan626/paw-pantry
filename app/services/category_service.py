
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Category
from app.repositories.category_repository import (
    create_category,
    get_all_categories,
)
from app.schemas.category import CategoryCreate


def list_categories(db: Session) -> list[Category]:
    return get_all_categories(db)


def create_category_service(
    db: Session,
    category_data: CategoryCreate,
) -> Category:
    # Check whether the slug already exists.
    existing_category = db.scalar(
        select(Category).where(
            Category.slug == category_data.slug,
            Category.deleted_at.is_(None),
        )
    )

    if existing_category:
        raise ValueError("A category with this slug already exists.")

    # Validate the parent category, if provided.
    if category_data.parent_id is not None:
        parent_category = db.scalar(
            select(Category).where(
                Category.id == category_data.parent_id,
                Category.deleted_at.is_(None),
            )
        )

        if parent_category is None:
            raise ValueError("Parent category does not exist.")

    return create_category(db, category_data)
