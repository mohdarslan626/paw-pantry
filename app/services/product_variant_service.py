
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import ProductVariant
from app.repositories.product_variant_repository import (
    create_product_variant,
    get_product_for_variant,
    get_variant_by_id,
    list_product_variants,
    soft_delete_product_variant,
    update_product_variant,
)
from app.schemas.product import (
    ProductVariantCreate,
    ProductVariantUpdate,
)


def list_product_variants_service(
    db: Session,
    product_id: UUID,
) -> list[ProductVariant]:
    product = get_product_for_variant(db, product_id)
    if product is None:
        raise ValueError("Product not found.")

    return list_product_variants(db, product_id)


def create_product_variant_service(
    db: Session,
    product_id: UUID,
    variant_data: ProductVariantCreate,
) -> ProductVariant:
    product = get_product_for_variant(db, product_id)
    if product is None:
        raise ValueError("Product not found.")

    data = variant_data.model_dump()
    data["sku"] = data["sku"].strip()
    data["variant_name"] = data["variant_name"].strip()
    data["currency"] = data["currency"].upper()

    if not data["sku"]:
        raise ValueError("SKU cannot be blank.")
    if not data["variant_name"]:
        raise ValueError("Variant name cannot be blank.")

    return create_product_variant(db, product_id, data)


def update_product_variant_service(
    db: Session,
    variant_id: UUID,
    update_data: ProductVariantUpdate,
) -> ProductVariant | None:
    variant = get_variant_by_id(db, variant_id)
    if variant is None:
        return None

    data = update_data.model_dump(exclude_unset=True)

    if "sku" in data:
        if data["sku"] is None or not data["sku"].strip():
            raise ValueError("SKU cannot be blank.")
        data["sku"] = data["sku"].strip()

    if "variant_name" in data:
        if data["variant_name"] is None or not data["variant_name"].strip():
            raise ValueError("Variant name cannot be blank.")
        data["variant_name"] = data["variant_name"].strip()

    if "weight_grams" in data and data["weight_grams"] is None:
        # Weight is optional, so explicitly allowing null is valid.
        pass

    if "price" in data and data["price"] is None:
        raise ValueError("Price cannot be null.")

    if "currency" in data:
        if data["currency"] is None or len(data["currency"].strip()) != 3:
            raise ValueError("Currency must contain three characters.")
        data["currency"] = data["currency"].strip().upper()

    return update_product_variant(db, variant, data)


def delete_product_variant_service(
    db: Session,
    variant_id: UUID,
) -> bool:
    variant = get_variant_by_id(db, variant_id)
    if variant is None:
        return False

    soft_delete_product_variant(db, variant)
    return True
