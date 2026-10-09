from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Date, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PurchaseOrderStatus(str, Enum):
    DRAFT = "Draft"
    APPROVED = "Approved"
    PARTIALLY_RECEIVED = "Partially Received"
    RECEIVED = "Received"
    CANCELLED = "Cancelled"


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    po_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id"),
        nullable=False,
        index=True
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=False,
        index=True
    )

    expected_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    received_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=0
    )

    status: Mapped[PurchaseOrderStatus] = mapped_column(
        SQLEnum(PurchaseOrderStatus),
        nullable=False,
        default=PurchaseOrderStatus.DRAFT,
        index=True
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

    supplier = relationship(
        "Supplier",
        backref="purchase_orders"
    )

    warehouse = relationship(
        "Warehouse",
        backref="purchase_orders"
    )

    items = relationship(
        "PurchaseOrderItem",
        back_populates="purchase_order",
        cascade="all, delete-orphan"
    )


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    purchase_order_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.id"),
        nullable=False,
        index=True
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
        index=True
    )

    ordered_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    received_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0
    )

    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False
    )

    purchase_order = relationship(
        "PurchaseOrder",
        back_populates="items"
    )

    product = relationship(
        "Product",
        backref="purchase_order_items"
    )