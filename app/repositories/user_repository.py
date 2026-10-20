
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import User


def get_active_user_by_email(db: Session, email_normalized: str) -> User | None:
    statement = select(User).where(
        User.email_normalized == email_normalized,
        User.deleted_at.is_(None),
    )
    return db.scalar(statement)


def create_user(db: Session, user_data: dict) -> User:
    user = User(**user_data)

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise


def get_user_for_login(db: Session, email_normalized: str) -> User | None:
    statement = select(User).where(
        User.email_normalized == email_normalized,
        User.deleted_at.is_(None),
    )
    return db.scalar(statement)
