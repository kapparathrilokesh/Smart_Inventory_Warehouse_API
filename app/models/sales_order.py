from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SalesOrderStatus(str, Enum):
    DRAFT = "Draft"
    CONFIRMED = "Confirmed"
    PICKED = "Picked"
    PACKED = "Packed"
    DISPATCHED = "Dispatched"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    so_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False,
        index=True
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=False,
        index=True
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=0
    )

    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=0
    )

    grand_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=0
    )

    status: Mapped[SalesOrderStatus] = mapped_column(
        SQLEnum(SalesOrderStatus),
        nullable=False,
        default=SalesOrderStatus.DRAFT,
        index=True
    )

    courier: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    tracking_number: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True
    )

    dispatched_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    customer = relationship(
        "Customer",
        backref="sales_orders"
    )

    warehouse = relationship(
        "Warehouse",
        backref="sales_orders"
    )

    items = relationship(
        "SalesOrderItem",
        back_populates="sales_order",
        cascade="all, delete-orphan"
    )


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    sales_order_id: Mapped[int] = mapped_column(
        ForeignKey("sales_orders.id"),
        nullable=False,
        index=True
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
        index=True
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False
    )

    sales_order = relationship(
        "SalesOrder",
        back_populates="items"
    )

    product = relationship(
        "Product",
        backref="sales_order_items"
    )