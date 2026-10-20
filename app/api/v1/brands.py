
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import User
from app.schemas.brand import BrandCreate, BrandResponse, BrandUpdate
from app.services.brand_service import (create_brand_service, get_brand_service, list_brands, update_brand_service, delete_brand_service)
from app.core.dependencies import require_admin

router = APIRouter(prefix="/brands", tags=["Brands"])


@router.get("/", response_model=list[BrandResponse])
def get_brands(
    db: Session = Depends(get_db),
) -> list[BrandResponse]:
    return list_brands(db)


@router.get("/{brand_id}", response_model=BrandResponse)
def get_brand_endpoint(
    brand_id: int,
    db: Session = Depends(get_db),
) -> BrandResponse:
    try:
        return get_brand_service(db, brand_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

@router.post(
    "/",
    response_model=BrandResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_brand_endpoint(
    brand_data: BrandCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> BrandResponse:
    try:
        return create_brand_service(db, brand_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Brand conflicts with an existing database record.",
        ) from exc


@router.patch("/{brand_id}", response_model=BrandResponse)
def update_brand_endpoint(
    brand_id: int,
    update_data: BrandUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> BrandResponse:
    try:
        return update_brand_service(db, brand_id, update_data)
    except ValueError as exc:
        message = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if message == "Brand not found."
            else status.HTTP_409_CONFLICT
            if message == "A brand with this slug already exists."
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        raise HTTPException(
            status_code=status_code,
            detail=message,
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Brand conflicts with an existing database record.",
        ) from exc

@router.delete(
    "/{brand_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_brand_endpoint(
    brand_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Response:
    try:
        delete_brand_service(db, brand_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    