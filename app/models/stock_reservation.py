
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Numeric,
    Enum,
)
from sqlalchemy.sql import func
from app.database import Base
import enum


class ReservationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"


class StockReservation(Base):
    __tablename__ = "stock_reservations"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(
        Integer, ForeignKey("products.id"), nullable=False
    )
    warehouse_id = Column(
        Integer, ForeignKey("warehouses.id"), nullable=False
    )
    sales_order_id = Column(
        Integer, ForeignKey("sales_orders.id"), nullable=True
    )
    quantity = Column(Numeric(12, 2), nullable=False)
    status = Column(
        Enum(ReservationStatus),
        default=ReservationStatus.ACTIVE,
        nullable=False,
    )
    reserved_by = Column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(
        DateTime, server_default=func.now(),
        onupdate=func.now()
    )
