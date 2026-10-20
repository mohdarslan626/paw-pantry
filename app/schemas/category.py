
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from pydantic import BaseModel, ConfigDict, Field

class CategoryResponse(BaseModel):
    id: int
    parent_id: int | None
    name: str
    slug: str
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(min_length=2, max_length=180, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = None
    parent_id: int | None = None
