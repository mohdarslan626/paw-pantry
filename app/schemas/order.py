
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from app.models.models import OrderStatus

class CheckoutRequest(BaseModel):
    shipping_address_id: UUID
    idempotency_key: str = Field(min_length=8, max_length=255)


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    variant_id: UUID | None
    sku_snapshot: str
    name_snapshot: str
    unit_price: Decimal
    quantity: int


class CheckoutResponse(BaseModel):
    id: UUID
    order_number: str
    status: str
    currency: str
    subtotal_amount: Decimal
    shipping_amount: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    shipping_address_snapshot: dict
    items: list[OrderItemResponse]


from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrderHistoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    variant_id: UUID | None
    sku_snapshot: str
    name_snapshot: str
    unit_price: Decimal
    quantity: int


class OrderHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_number: str
    status: OrderStatus
    currency: str
    subtotal_amount: Decimal
    shipping_amount: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    shipping_address_snapshot: dict
    created_at: datetime
    items: list[OrderHistoryItemResponse]



class ShipmentTrackingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    carrier: str | None
    tracking_number: str | None
    status: str
    shipped_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime


class OrderStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    old_status: str | None
    new_status: str
    reason: str | None
    created_at: datetime


class OrderDetailResponse(OrderHistoryResponse):
    billing_address_snapshot: dict | None = None
    shipments: list[ShipmentTrackingResponse] = Field(default_factory=list)
    status_history: list[OrderStatusHistoryResponse] = Field(default_factory=list)

class ShipmentCreateRequest(BaseModel):
    """Shipment details supplied by an administrator."""

    carrier: str = Field(min_length=1, max_length=100)
    tracking_number: str = Field(min_length=1, max_length=160)


class ShipmentStatusUpdateRequest(BaseModel):
    """Only forward shipment transitions are accepted by the API."""

    status: str = Field(pattern=r"^(in_transit|delivered)$")
