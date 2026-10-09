from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(
        default=None,
        max_length=500
    )


class CategoryUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )
    description: str | None = Field(
        default=None,
        max_length=500
    )
    is_active: bool | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: int | None