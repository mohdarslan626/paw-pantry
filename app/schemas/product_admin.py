from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import datetime

from app.schemas.product import (
    ProductVariantResponse,
    ProductImageResponse,
    ProductIngredientResponse,
    NutritionalAnalysisResponse,
)


class ProductImageCreate(BaseModel):
    media_asset_id: UUID
    alt_text: str | None = Field(default=None, max_length=255)
    is_primary: bool = False


class ProductImageUpdate(BaseModel):
    alt_text: str | None = Field(default=None, max_length=255)
    is_primary: bool | None = None
    position: int | None = Field(default=None, ge=0)


class IngredientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None


class IngredientResponse(BaseModel):
    id: int
    name: str
    description: str | None
    model_config = ConfigDict(from_attributes=True)


class ProductIngredientCreate(BaseModel):
    ingredient_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    percentage: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    display_order: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def require_ingredient_reference(self):
        if self.ingredient_id is None and not self.name:
            raise ValueError("Provide ingredient_id or a new ingredient name.")
        if self.ingredient_id is not None and self.name:
            raise ValueError("Provide either ingredient_id or name, not both.")
        return self


class ProductIngredientUpdate(BaseModel):
    percentage: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    display_order: int | None = Field(default=None, ge=0)


class NutritionCreate(BaseModel):
    nutrient_code: str = Field(min_length=1, max_length=80)
    value: Decimal = Field(ge=0, max_digits=12, decimal_places=5)
    unit: str = Field(min_length=1, max_length=32)
    basis: str = Field(default="as_fed", min_length=1, max_length=32)


class NutritionUpdate(BaseModel):
    value: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=5)
    unit: str | None = Field(default=None, min_length=1, max_length=32)
    basis: str | None = Field(default=None, min_length=1, max_length=32)

class ProductAdminResponse(BaseModel):
    id: UUID
    brand_id: int | None
    category_id: int
    name: str
    slug: str
    short_description: str | None
    description: str | None
    status: str
    fulfillment_type: str
    external_url: str | None
    external_marketplace: str | None
    created_at: datetime

    variants: list[ProductVariantResponse] = Field(default_factory=list)
    images: list[ProductImageResponse] = Field(default_factory=list)
    ingredients: list[ProductIngredientResponse] = Field(default_factory=list)
    nutrition: list[NutritionalAnalysisResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
