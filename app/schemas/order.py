
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
