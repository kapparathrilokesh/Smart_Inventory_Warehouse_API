from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProductUnit(str, Enum):
    PIECE = "Piece"
    BOX = "Box"
    KG = "Kg"
    LITRE = "Litre"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True
    )

    sku: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    barcode: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"),
        nullable=False
    )

    unit: Mapped[ProductUnit] = mapped_column(
        SQLEnum(ProductUnit),
        nullable=False
    )

    cost_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    selling_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    reorder_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    reorder_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    preferred_supplier_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
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

    category = relationship(
        "Category",
        backref="products"
    )