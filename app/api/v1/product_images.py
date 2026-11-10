from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.models import MediaAsset, MediaStatus, Product, ProductImage, User
from app.schemas.product_admin import ProductImageCreate, ProductImageUpdate
from app.schemas.product import ProductImageResponse

router = APIRouter(prefix="/products/{product_id}/images", tags=["Product Images"])

@router.get("/", response_model=list[ProductImageResponse])
def list_product_images(product_id: UUID, db: Session = Depends(get_db)):
    return db.scalars(select(ProductImage).where(ProductImage.product_id == product_id, ProductImage.deleted_at.is_(None)).options(selectinload(ProductImage.media_asset)).order_by(ProductImage.position)).all()

@router.post("/", response_model=ProductImageResponse, status_code=status.HTTP_201_CREATED)
def add_product_image(product_id: UUID, payload: ProductImageCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    product = db.get(Product, product_id)
    asset = db.get(MediaAsset, payload.media_asset_id)
    if product is None or product.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Product not found.")
    if asset is None or asset.deleted_at is not None or asset.status != MediaStatus.READY:
        raise HTTPException(status_code=404, detail="Ready media asset not found.")
    position = db.scalar(select(func.coalesce(func.max(ProductImage.position), -1)).where(ProductImage.product_id == product_id, ProductImage.deleted_at.is_(None))) + 1
    if payload.is_primary:
        db.query(ProductImage).filter(ProductImage.product_id == product_id, ProductImage.deleted_at.is_(None)).update({ProductImage.is_primary: False}, synchronize_session=False)
    image = ProductImage(product_id=product_id, media_asset_id=asset.id, alt_text=payload.alt_text, position=position, is_primary=payload.is_primary)
    db.add(image)
    try:
        db.commit(); db.refresh(image)
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(status_code=409, detail="This image is already linked to the product.") from exc
    return db.scalar(select(ProductImage).where(ProductImage.id == image.id).options(selectinload(ProductImage.media_asset)))

@router.patch("/{image_id}", response_model=ProductImageResponse)
def update_product_image(product_id: UUID, image_id: UUID, payload: ProductImageUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    image = db.scalar(select(ProductImage).where(ProductImage.id == image_id, ProductImage.product_id == product_id, ProductImage.deleted_at.is_(None)))
    if image is None: raise HTTPException(status_code=404, detail="Product image not found.")
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_primary"):
        db.query(ProductImage).filter(ProductImage.product_id == product_id, ProductImage.id != image_id, ProductImage.deleted_at.is_(None)).update({ProductImage.is_primary: False}, synchronize_session=False)
    for key, value in data.items(): setattr(image, key, value)
    db.commit()
    return db.scalar(select(ProductImage).where(ProductImage.id == image_id).options(selectinload(ProductImage.media_asset)))

@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_image(product_id: UUID, image_id: UUID, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    image = db.scalar(select(ProductImage).where(ProductImage.id == image_id, ProductImage.product_id == product_id, ProductImage.deleted_at.is_(None)))
    if image is None: raise HTTPException(status_code=404, detail="Product image not found.")
    from datetime import datetime, timezone
    image.deleted_at = datetime.now(timezone.utc)
    db.commit()
