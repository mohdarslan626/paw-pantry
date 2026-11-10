
from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_admin
from app.db.session import get_db
from app.models.models import User
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import (
    create_product_service,
    delete_product_service,
    get_product_service,
    list_products_service,
    update_product_service,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.models import (
    User,
    Product,
    ProductVariant,
    ProductImage,
    ProductIngredient,
    NutritionalAnalysis,
    MediaAsset,
    Ingredient,
)

from app.schemas.product_admin import ProductAdminResponse
from app.services.storage import get_storage

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=list[ProductResponse])
def get_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    category_id: int | None = Query(default=None, gt=0),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    sort_by: str = Query(default="name", pattern="^(name|created_at|price)$"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
) -> list:

    if (
    min_price is not None
    and max_price is not None
    and min_price > max_price
    ):
        raise HTTPException(
            status_code=422,
            detail="min_price must be less than or equal to max_price.",
        )
    
    return list_products_service(
        db,
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        sort_order=sort_order,
    )

@router.get("/admin", response_model=list[ProductAdminResponse])
def get_admin_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    sort_by: str = Query(
        default="created_at",
        pattern="^(name|created_at|price)$",
    ),
    sort_order: str = Query(
        default="desc",
        pattern="^(asc|desc)$",
    ),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    products = list_products_service(
        db,
        include_drafts=True,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    storage = get_storage()
    result = []

    for product in products:
        images = []

        for image in product.images:
            media = image.media_asset

            if media is None or media.deleted_at is not None:
                continue

            images.append({
                "id": image.id,
                "media_asset_id": image.media_asset_id,
                "alt_text": image.alt_text,
                "position": image.position,
                "is_primary": image.is_primary,
                "media_asset": {
                    "id": media.id,
                    "object_key": media.object_key,
                    "mime_type": media.mime_type,
                    "status": media.status.value,
                    "url": storage.url_for(media.object_key),
                },
            })

        ingredients = [
            {
                "id": item.id,
                "ingredient_id": item.ingredient_id,
                "percentage": item.percentage,
                "display_order": item.display_order,
                "ingredient_name": item.ingredient.name,
            }
            for item in product.ingredients
            if item.deleted_at is None
        ]

        nutrition = [
            item
            for item in product.nutrition
            if item.deleted_at is None
        ]

        result.append({
            "id": product.id,
            "brand_id": product.brand_id,
            "category_id": product.category_id,
            "name": product.name,
            "slug": product.slug,
            "short_description": product.short_description,
            "description": product.description,
            "status": product.status.value,
            "fulfillment_type": product.fulfillment_type.value,
            "external_url": product.external_url,
            "external_marketplace": (
                product.external_marketplace.value
                if product.external_marketplace else None
            ),
            "created_at": product.created_at,
            "variants": [
                variant
                for variant in product.variants
                if variant.deleted_at is None
            ],
            "images": images,
            "ingredients": ingredients,
            "nutrition": nutrition,
        })

    return result

@router.get("/{product_id:uuid}", response_model=ProductResponse)
def get_product(
    product_id: UUID,
    db: Session = Depends(get_db),
):
    product = get_product_service(db, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    return product

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product_endpoint(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    try:
        return create_product_service(db, product_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Product conflicts with an existing database record.",
        ) from exc


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product_endpoint(
    product_id: UUID,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    try:
        product = update_product_service(db, product_id, product_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Product conflicts with an existing database record.",
        ) from exc

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_endpoint(
    product_id: UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    if not delete_product_service(db, product_id):
        raise HTTPException(status_code=404, detail="Product not found.")
