from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, EmailStr


class SupplierCreate(BaseModel):
    supplier_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=10)
    gst_number: str | None = Field(default=None, max_length=20)
    address: str | None = None
    lead_time_days: int = Field(default=0, ge=0)


class SupplierUpdate(BaseModel):
    supplier_code: str | None = Field(
        default=None, min_length=1, max_length=50
    )
    name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=10)
    gst_number: str | None = Field(default=None, max_length=20)
    address: str | None = None
    lead_time_days: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_code: str
    name: str
    email: str
    phone: str | None
    gst_number: str | None
    address: str | None
    lead_time_days: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: int | None