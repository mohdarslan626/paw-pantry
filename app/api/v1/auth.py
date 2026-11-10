
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import UserRegister, UserResponse, UserLogin, TokenResponse
from app.services.auth_service import register_user, login_user

from app.core.dependencies import get_current_user
from app.models.models import User
import logging

from app.schemas.auth import (
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordResetResponse,
)
from app.services.password_reset_service import (
    request_password_reset,
    reset_password,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
) -> UserResponse:
    try:
        return register_user(db, user_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        access_token = login_user(db, credentials)
        return TokenResponse(access_token=access_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        roles=[
            role.name.strip().lower()
            for role in current_user.roles
            if role.deleted_at is None
        ],
    )


@router.post(
    "/forgot-password",
    response_model=PasswordResetResponse,
)
def forgot_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
) -> PasswordResetResponse:
    try:
        request_password_reset(db, str(request.email))
    except Exception:
        db.rollback()
        logger.exception("Password reset request failed.")

    return PasswordResetResponse(
        message=(
            "If an eligible account exists for that email, "
            "a password reset link has been sent."
        )
    )


@router.post(
    "/reset-password",
    response_model=PasswordResetResponse,
)
def confirm_password_reset(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db),
) -> PasswordResetResponse:
    try:
        success = reset_password(
            db,
            request.token,
            request.new_password,
        )
    except Exception:
        db.rollback()
        logger.exception("Password reset failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to reset password. Please try again.",
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset link.",
        )

    return PasswordResetResponse(
        message="Your password has been reset successfully."
    )
