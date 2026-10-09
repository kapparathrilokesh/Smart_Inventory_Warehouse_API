
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    warehouse_id: int
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    available_quantity: Decimal


class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    warehouse_id: int
    movement_type: str
    quantity: Decimal
    reference_id: int | None
    balance_after: Decimal
    performed_by: int


class StockReceiptRequest(BaseModel):
    product_id: int = Field(gt=0)
    warehouse_id: int = Field(gt=0)
    quantity: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2
    )
