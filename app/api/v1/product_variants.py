
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.models import User
from app.schemas.product import (
    ProductVariantCreate,
    ProductVariantResponse,
    ProductVariantUpdate,
)
from app.services.product_variant_service import (
    create_product_variant_service,
    delete_product_variant_service,
    list_product_variants_service,
    update_product_variant_service,
)

router = APIRouter(
    prefix="/products/{product_id}/variants",
    tags=["Product Variants"],
)


@router.get("/", response_model=list[ProductVariantResponse])
def get_product_variants(
    product_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        return list_product_variants_service(db, product_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/", response_model=ProductVariantResponse, status_code=status.HTTP_201_CREATED)
def create_product_variant_endpoint(
    product_id: UUID,
    variant_data: ProductVariantCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    try:
        return create_product_variant_service(db, product_id, variant_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Variant conflicts with an existing database record.",
        ) from exc


@router.patch("/{variant_id}", response_model=ProductVariantResponse)
def update_product_variant_endpoint(
    product_id: UUID,
    variant_id: UUID,
    variant_data: ProductVariantUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    # Ensure the variant belongs to the product in the URL.
    from app.repositories.product_variant_repository import get_variant_by_id

    variant = get_variant_by_id(db, variant_id)
    if variant is None or variant.product_id != product_id:
        raise HTTPException(status_code=404, detail="Variant not found.")

    try:
        updated = update_product_variant_service(db, variant_id, variant_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Variant conflicts with an existing database record.",
        ) from exc

    if updated is None:
        raise HTTPException(status_code=404, detail="Variant not found.")
    return updated


@router.delete("/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_variant_endpoint(
    product_id: UUID,
    variant_id: UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    from app.repositories.product_variant_repository import get_variant_by_id

    variant = get_variant_by_id(db, variant_id)
    if variant is None or variant.product_id != product_id:
        raise HTTPException(status_code=404, detail="Variant not found.")

    if not delete_product_variant_service(db, variant_id):
        raise HTTPException(status_code=404, detail="Variant not found.")
