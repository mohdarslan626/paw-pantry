
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Category
from app.schemas.category import CategoryCreate


def get_all_categories(db: Session) -> list[Category]:
    statement = (
        select(Category)
        .where(Category.deleted_at.is_(None))
        .order_by(Category.name.asc())
    )

    return list(db.scalars(statement).all())


def create_category(db: Session, category_data: CategoryCreate) -> Category:
    category = Category(
        name=category_data.name,
        slug=category_data.slug,
        description=category_data.description,
        parent_id=category_data.parent_id,
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return category
