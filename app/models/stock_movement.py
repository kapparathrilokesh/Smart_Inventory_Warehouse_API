from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MovementType(str, Enum):
    PURCHASE_RECEIPT = "Purchase Receipt"
    SALE_DISPATCH = "Sale Dispatch"
    CUSTOMER_RETURN = "Customer Return"


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
        index=True
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=False,
        index=True
    )

    movement_type: Mapped[MovementType] = mapped_column(
        SQLEnum(MovementType),
        nullable=False,
        index=True
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    reference_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    performed_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    product = relationship(
        "Product",
        backref="stock_movements"
    )

    warehouse = relationship(
        "Warehouse",
        backref="stock_movements"
    )

    performer = relationship(
        "User",
        foreign_keys=[performed_by]
    )