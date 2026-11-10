from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


class InventoryLocationCreate(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=160)


class InventoryLocationResponse(BaseModel):
    id: int
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


def validate_nonzero_quantity(value: int) -> int:
    if value == 0:
        raise ValueError("Quantity adjustment cannot be zero.")
    return value


class InventoryAdjustment(BaseModel):
    variant_id: UUID
    location_id: int = Field(gt=0)
    quantity_delta: Annotated[int, AfterValidator(validate_nonzero_quantity)]
    reason: str = Field(min_length=1, max_length=80)


class InventoryItemResponse(BaseModel):
    id: UUID
    variant_id: UUID
    product_name: str
    variant_name: str
    sku: str
    location_id: int
    location_name: str
    on_hand: int
    reserved: int
    available: int


class InventoryMovementResponse(BaseModel):
    id: UUID
    variant_id: UUID
    product_name: str
    variant_name: str
    sku: str
    location_id: int
    location_name: str
    quantity_delta: int
    reason: str
    created_at: datetime
