
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AddressCreate(BaseModel):
    recipient_name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    line1: str = Field(min_length=1, max_length=255)
    line2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=120)
    state_region: str = Field(min_length=1, max_length=120)
    postal_code: str = Field(min_length=1, max_length=24)
    country_code: str = Field(default="IN", min_length=2, max_length=2)
    is_default: bool = False


class AddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    address_type: str
    recipient_name: str
    phone: str | None
    line1: str
    line2: str | None
    city: str
    state_region: str
    postal_code: str
    country_code: str
    is_default: bool
    created_at: datetime
