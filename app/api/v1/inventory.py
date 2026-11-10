from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.models import User
from app.schemas.inventory_admin import (
    InventoryAdjustment,
    InventoryItemResponse,
    InventoryLocationCreate,
    InventoryLocationResponse,
    InventoryMovementResponse,
)
from app.services.inventory_service import (
    adjust_inventory_service,
    create_location_service,
    list_inventory_movements_service,
    list_inventory_service,
    list_locations_service,
)

router = APIRouter(prefix="/admin/inventory", tags=["Admin Inventory"])


@router.get("/locations", response_model=list[InventoryLocationResponse])
def get_inventory_locations(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return list_locations_service(db)


@router.post(
    "/locations",
    response_model=InventoryLocationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_inventory_location(
    location_data: InventoryLocationCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        return create_location_service(
            db,
            code=location_data.code,
            name=location_data.name,
            user_id=admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An inventory location with this code already exists.",
        ) from exc


@router.get("", response_model=list[InventoryItemResponse])
def get_admin_inventory(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return list_inventory_service(db)


@router.post("/adjustments", response_model=InventoryItemResponse)
def adjust_admin_inventory(
    adjustment: InventoryAdjustment,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        inventory = adjust_inventory_service(
            db,
            variant_id=adjustment.variant_id,
            location_id=adjustment.location_id,
            quantity_delta=adjustment.quantity_delta,
            reason=adjustment.reason,
            user_id=admin.id,
        )
        return next(
            item for item in list_inventory_service(db)
            if item["id"] == inventory.id
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Inventory adjustment conflicted with another request.",
        ) from exc


@router.get("/movements", response_model=list[InventoryMovementResponse])
def get_inventory_movements(
    variant_id: UUID | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return list_inventory_movements_service(
        db,
        variant_id=variant_id,
        skip=skip,
        limit=limit,
    )
