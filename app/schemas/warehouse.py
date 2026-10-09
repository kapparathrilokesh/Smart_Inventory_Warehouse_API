from pydantic import BaseModel, ConfigDict, Field


class WarehouseCreate(BaseModel):
    warehouse_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=2, max_length=150)
    city: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=500)
    capacity: int = Field(gt=0)
    manager_id: int | None = None


class WarehouseUpdate(BaseModel):
    warehouse_code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=2, max_length=150)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    capacity: int | None = Field(default=None, gt=0)
    manager_id: int | None = None
    is_active: bool | None = None


class WarehouseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warehouse_code: str
    name: str
    city: str
    address: str
    capacity: int
    manager_id: int | None
    is_active: bool