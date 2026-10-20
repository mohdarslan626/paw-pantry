
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.security import verify_password, create_access_token
from app.models.models import UserStatus
from app.repositories.user_repository import get_user_for_login
from app.schemas.auth import UserLogin

from app.core.security import hash_password
from app.repositories.user_repository import (
    create_user,
    get_active_user_by_email,
)
from app.schemas.auth import UserRegister


def register_user(db: Session, user_data: UserRegister):
    normalized_email = str(user_data.email).strip().lower()

    existing_user = get_active_user_by_email(db, normalized_email)
    if existing_user is not None:
        raise ValueError("An account with this email already exists.")

    user = create_user(
        db,
        {
            "email": str(user_data.email).strip(),
            "email_normalized": normalized_email,
            "password_hash": hash_password(user_data.password),
            "display_name": user_data.display_name,
        },
    )
    return user


def login_user(db: Session, credentials: UserLogin) -> str:
    normalized_email = str(credentials.email).strip().lower()
    user = get_user_for_login(db, normalized_email)

    # Use the same error for unknown emails and incorrect passwords.
    if (
        user is None
        or user.password_hash is None
        or not verify_password(credentials.password, user.password_hash)
    ):
        raise ValueError("Invalid email or password.")

    if user.status != UserStatus.ACTIVE:
        raise ValueError("Invalid email or password.")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return create_access_token(str(user.id))
