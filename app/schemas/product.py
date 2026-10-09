from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.product import ProductUnit


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    sku: str = Field(min_length=1, max_length=100)
    barcode: str | None = Field(default=None, max_length=100)
    category_id: int
    unit: ProductUnit
    cost_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    selling_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reorder_level: int = Field(default=0, ge=0)
    reorder_quantity: int = Field(default=0, ge=0)
    preferred_supplier_id: int | None = None

    @model_validator(mode="after")
    def validate_prices(self):
        if self.selling_price < self.cost_price:
            raise ValueError("Selling price must be greater than or equal to cost price")
        return self


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    barcode: str | None = Field(default=None, max_length=100)
    category_id: int | None = None
    unit: ProductUnit | None = None
    cost_price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    selling_price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    reorder_level: int | None = Field(default=None, ge=0)
    reorder_quantity: int | None = Field(default=None, ge=0)
    preferred_supplier_id: int | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sku: str
    barcode: str | None
    category_id: int
    unit: ProductUnit
    cost_price: Decimal
    selling_price: Decimal
    reorder_level: int
    reorder_quantity: int
    preferred_supplier_id: int | None
    is_active: bool
