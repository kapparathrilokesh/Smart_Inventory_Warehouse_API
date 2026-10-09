
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from decimal import Decimal
from datetime import datetime
from app.models.stock_reservation import ReservationStatus


class StockReservationCreate(BaseModel):
    product_id: int = Field(gt=0)
    warehouse_id: int = Field(gt=0)
    quantity: Decimal = Field(gt=0)
    sales_order_id: Optional[int] = Field(default=None, gt=0)


class StockReservationResponse(BaseModel):
    id: int
    product_id: int
    warehouse_id: int
    sales_order_id: Optional[int]
    quantity: Decimal
    status: ReservationStatus
    reserved_by: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
