import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.models import (
    PasswordResetToken,
    User,
    UserStatus,
)
from app.repositories.user_repository import get_active_user_by_email
from app.services.email_service import send_password_reset_email


logger = logging.getLogger(__name__)


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def request_password_reset(
    db: Session,
    email: str,
) -> None:
    normalized_email = email.strip().lower()
    user = get_active_user_by_email(db, normalized_email)

    # Do not reveal whether an account exists or supports password login.
    if (
        user is None
        or user.status != UserStatus.ACTIVE
        or user.password_hash is None
    ):
        return

    settings = get_settings()
    now = datetime.now(timezone.utc)

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_reset_token(raw_token)

    try:
        # Invalidate previous unused tokens for this user.
        previous_tokens = db.scalars(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
        ).all()

        for previous_token in previous_tokens:
            previous_token.used_at = now

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(
                minutes=settings.password_reset_token_expire_minutes
            ),
        )

        db.add(reset_token)
        db.commit()

    except Exception:
        db.rollback()
        raise

    reset_url = (
        f"{settings.frontend_url.rstrip('/')}"
        f"/reset-password?token={raw_token}"
    )

    try:
        send_password_reset_email(
            recipient_email=user.email,
            reset_url=reset_url,
        )
    except RuntimeError:
        # Prevent a token from remaining usable if email delivery fails.
        reset_token.used_at = datetime.now(timezone.utc)
        db.commit()
        logger.exception("Password reset email delivery failed.")


def reset_password(
    db: Session,
    token: str,
    new_password: str,
) -> bool:
    token_hash = _hash_reset_token(token)
    now = datetime.now(timezone.utc)

    reset_token = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash)
        .with_for_update()
    )

    if (
        reset_token is None
        or reset_token.used_at is not None
        or reset_token.expires_at <= now
    ):
        return False

    user = db.scalar(
        select(User).where(
            User.id == reset_token.user_id,
            User.deleted_at.is_(None),
        )
    )

    if (
        user is None
        or user.status != UserStatus.ACTIVE
        or user.password_hash is None
    ):
        return False

    try:
        user.password_hash = hash_password(new_password)
        reset_token.used_at = now

        # Invalidate every other unused reset token for this user.
        other_tokens = db.scalars(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.id != reset_token.id,
            )
        ).all()

        for other_token in other_tokens:
            other_token.used_at = now

        db.commit()
        return True

    except Exception:
        db.rollback()
        raise
