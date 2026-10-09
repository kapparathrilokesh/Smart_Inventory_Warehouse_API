
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.purchase_order import PurchaseOrderStatus


class PurchaseOrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    ordered_quantity: Decimal = Field(
        gt=0, max_digits=12, decimal_places=2
    )
    unit_cost: Decimal = Field(
        gt=0, max_digits=12, decimal_places=2
    )


class PurchaseOrderCreate(BaseModel):
    supplier_id: int = Field(gt=0)
    warehouse_id: int = Field(gt=0)
    expected_date: date | None = None
    items: list[PurchaseOrderItemCreate] = Field(min_length=1)


class PurchaseOrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    ordered_quantity: Decimal
    received_quantity: Decimal
    unit_cost: Decimal
    line_total: Decimal


class PurchaseOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    po_number: str
    supplier_id: int
    warehouse_id: int
    expected_date: date | None
    received_at: datetime | None
    total_amount: Decimal
    status: PurchaseOrderStatus
    created_at: datetime
    updated_at: datetime
    created_by: int | None
    items: list[PurchaseOrderItemResponse]


class PurchaseOrderReceiveItem(BaseModel):
    item_id: int = Field(gt=0)
    received_quantity: Decimal = Field(
        gt=0, max_digits=12, decimal_places=2
    )


class PurchaseOrderReceive(BaseModel):
    items: list[PurchaseOrderReceiveItem] = Field(min_length=1)
