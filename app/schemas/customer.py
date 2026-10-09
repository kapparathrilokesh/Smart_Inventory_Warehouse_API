
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerCreate(BaseModel):
    customer_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=10)
    address: str = Field(min_length=1, max_length=500)
    credit_limit: float = Field(default=0, ge=0)


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=10, max_length=10)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    credit_limit: float | None = Field(default=None, ge=0)
    is_active: bool | None = None


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_code: str
    name: str
    email: str
    phone: str
    address: str
    credit_limit: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: int | None
