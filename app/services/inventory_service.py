from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import (
    Inventory,
    InventoryLocation,
    InventoryMovement,
    Product,
    ProductFulfillmentType,
    ProductVariant,
)


def list_locations_service(db: Session) -> list[InventoryLocation]:
    statement = (
        select(InventoryLocation)
        .where(InventoryLocation.deleted_at.is_(None))
        .order_by(InventoryLocation.name)
    )
    return list(db.scalars(statement).all())


def create_location_service(
    db: Session,
    *,
    code: str,
    name: str,
    user_id: UUID,
) -> InventoryLocation:
    normalized_code = code.strip().upper()
    normalized_name = name.strip()

    if not normalized_code or not normalized_name:
        raise ValueError("Location code and name are required.")

    existing = db.scalar(
        select(InventoryLocation).where(
            InventoryLocation.code == normalized_code
        )
    )
    if existing is not None:
        raise ValueError("A location with this code already exists.")

    location = InventoryLocation(
        code=normalized_code,
        name=normalized_name,
        created_by=user_id,
    )
    db.add(location)

    try:
        db.commit()
        db.refresh(location)
        return location
    except Exception:
        db.rollback()
        raise


def list_inventory_service(db: Session) -> list[dict]:
    statement = (
        select(Inventory, ProductVariant, Product, InventoryLocation)
        .join(ProductVariant, Inventory.variant_id == ProductVariant.id)
        .join(Product, ProductVariant.product_id == Product.id)
        .join(InventoryLocation, Inventory.location_id == InventoryLocation.id)
        .where(
            Inventory.deleted_at.is_(None),
            ProductVariant.deleted_at.is_(None),
            Product.deleted_at.is_(None),
            InventoryLocation.deleted_at.is_(None),
        )
        .order_by(Product.name, ProductVariant.variant_name, InventoryLocation.name)
    )

    rows = db.execute(statement).all()

    return [
        {
            "id": inventory.id,
            "variant_id": variant.id,
            "product_name": product.name,
            "variant_name": variant.variant_name,
            "sku": variant.sku,
            "location_id": location.id,
            "location_name": location.name,
            "on_hand": inventory.on_hand,
            "reserved": inventory.reserved,
            "available": inventory.on_hand - inventory.reserved,
        }
        for inventory, variant, product, location in rows
    ]


def adjust_inventory_service(
    db: Session,
    *,
    variant_id: UUID,
    location_id: int,
    quantity_delta: int,
    reason: str,
    user_id: UUID,
) -> Inventory:
    if quantity_delta == 0:
        raise ValueError("Stock adjustment quantity cannot be zero.")

    variant = db.scalar(
        select(ProductVariant)
        .join(Product, Product.id == ProductVariant.product_id)
        .where(
            ProductVariant.id == variant_id,
            ProductVariant.deleted_at.is_(None),
            ProductVariant.is_active.is_(True),
            Product.deleted_at.is_(None),
            Product.fulfillment_type == ProductFulfillmentType.INTERNAL,
        )
        .with_for_update()
    )
    if variant is None:
        raise ValueError("Active internal product variant not found.")

    location = db.scalar(
        select(InventoryLocation)
        .where(
            InventoryLocation.id == location_id,
            InventoryLocation.deleted_at.is_(None),
        )
    )
    if location is None:
        raise ValueError("Inventory location not found.")

    inventory = db.scalar(
        select(Inventory)
        .where(
            Inventory.variant_id == variant_id,
            Inventory.location_id == location_id,
            Inventory.deleted_at.is_(None),
        )
        .with_for_update()
    )

    if inventory is None:
        inventory = Inventory(
            variant_id=variant_id,
            location_id=location_id,
            on_hand=0,
            reserved=0,
            created_by=user_id,
        )
        db.add(inventory)
        db.flush()

    new_quantity = inventory.on_hand + quantity_delta

    if new_quantity < 0:
        raise ValueError("Stock adjustment would make on-hand stock negative.")

    if new_quantity < inventory.reserved:
        raise ValueError(
            "Stock cannot be reduced below the currently reserved quantity."
        )

    inventory.on_hand = new_quantity
    inventory.updated_by = user_id

    movement = InventoryMovement(
        variant_id=variant_id,
        location_id=location_id,
        quantity_delta=quantity_delta,
        reason=reason.strip(),
        created_by=user_id,
    )
    db.add(movement)

    try:
        db.commit()
        db.refresh(inventory)
        return inventory
    except Exception:
        db.rollback()
        raise


def list_inventory_movements_service(
    db: Session,
    *,
    variant_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    statement = (
        select(InventoryMovement, ProductVariant, Product, InventoryLocation)
        .join(ProductVariant, InventoryMovement.variant_id == ProductVariant.id)
        .join(Product, ProductVariant.product_id == Product.id)
        .join(InventoryLocation, InventoryMovement.location_id == InventoryLocation.id)
        .where(
            InventoryMovement.deleted_at.is_(None),
            ProductVariant.deleted_at.is_(None),
            Product.deleted_at.is_(None),
            InventoryLocation.deleted_at.is_(None),
        )
    )

    if variant_id is not None:
        statement = statement.where(
            InventoryMovement.variant_id == variant_id
        )

    statement = (
        statement
        .order_by(InventoryMovement.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    rows = db.execute(statement).all()

    return [
        {
            "id": movement.id,
            "variant_id": variant.id,
            "product_name": product.name,
            "variant_name": variant.variant_name,
            "sku": variant.sku,
            "location_id": location.id,
            "location_name": location.name,
            "quantity_delta": movement.quantity_delta,
            "reason": movement.reason,
            "created_at": movement.created_at,
        }
        for movement, variant, product, location in rows
    ]
