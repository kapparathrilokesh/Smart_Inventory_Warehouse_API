
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.sales_order import SalesOrderStatus


class SalesOrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class SalesOrderCreate(BaseModel):
    customer_id: int = Field(gt=0)
    warehouse_id: int = Field(gt=0)
    tax_amount: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    items: list[SalesOrderItemCreate] = Field(min_length=1)


class SalesOrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class SalesOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    so_number: str
    customer_id: int
    warehouse_id: int
    subtotal: Decimal
    tax_amount: Decimal
    grand_total: Decimal
    status: SalesOrderStatus
    courier: str | None
    tracking_number: str | None
    dispatched_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime
    created_by: int | None
    items: list[SalesOrderItemResponse]


class SalesOrderDispatchRequest(BaseModel):
    courier: str = Field(min_length=2, max_length=100)
    tracking_number: str = Field(min_length=1, max_length=100)
