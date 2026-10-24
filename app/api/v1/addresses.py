
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.models import User, UserAddress
from app.schemas.address import AddressCreate, AddressResponse

router = APIRouter(prefix="/addresses", tags=["Addresses"])


@router.get("/", response_model=list[AddressResponse])
def list_addresses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(UserAddress)
        .where(
            UserAddress.user_id == current_user.id,
            UserAddress.deleted_at.is_(None),
        )
        .order_by(UserAddress.is_default.desc(), UserAddress.created_at.desc())
    )
    return db.scalars(statement).all()


@router.post(
    "/",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_address(
    payload: AddressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    address = UserAddress(
        user_id=current_user.id,
        address_type="shipping",
        recipient_name=payload.recipient_name,
        phone=payload.phone,
        line1=payload.line1,
        line2=payload.line2,
        city=payload.city,
        state_region=payload.state_region,
        postal_code=payload.postal_code,
        country_code=payload.country_code.upper(),
        is_default=payload.is_default,
    )

    if payload.is_default:
        existing = db.scalars(
            select(UserAddress).where(
                UserAddress.user_id == current_user.id,
                UserAddress.address_type == "shipping",
                UserAddress.is_default.is_(True),
                UserAddress.deleted_at.is_(None),
            )
        ).all()

        for item in existing:
            item.is_default = False

    db.add(address)
    db.commit()
    db.refresh(address)
    return address


@router.get("/{address_id}", response_model=AddressResponse)
def get_address(
    address_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    address = db.scalar(
        select(UserAddress).where(
            UserAddress.id == address_id,
            UserAddress.user_id == current_user.id,
            UserAddress.deleted_at.is_(None),
        )
    )

    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found.",
        )

    return address
