
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from app.models.models import ProductStatus


class ProductCreate(BaseModel):
    brand_id: int | None = None
    category_id: int
    name: str = Field(min_length=2, max_length=240)
    slug: str = Field(
        min_length=2,
        max_length=260,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = None


class ProductUpdate(BaseModel):
    brand_id: int | None = None
    category_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=240)
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=260,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = None
    status: ProductStatus | None = None

class ProductVariantCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    variant_name: str = Field(min_length=1, max_length=160)
    weight_grams: int | None = Field(default=None, gt=0)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    is_active: bool = True


class ProductVariantUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    variant_name: str | None = Field(
        default=None, min_length=1, max_length=160
    )
    weight_grams: int | None = Field(default=None, gt=0)
    price: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    currency: str | None = Field(
        default=None, min_length=3, max_length=3
    )
    is_active: bool | None = None

class ProductVariantResponse(BaseModel):
    id: UUID
    sku: str
    variant_name: str
    weight_grams: int | None
    price: Decimal
    currency: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class ProductResponse(BaseModel):
    id: UUID
    brand_id: int | None
    category_id: int
    name: str
    slug: str
    short_description: str | None
    description: str | None
    status: ProductStatus
    published_at: datetime | None
    created_at: datetime
    variants: list[ProductVariantResponse] = []

    model_config = ConfigDict(from_attributes=True)
