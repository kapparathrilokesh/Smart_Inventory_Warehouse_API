
from datetime import datetime
from decimal import Decimal
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.auth.dependencies import get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.customer import Customer
from app.models.warehouse import Warehouse
from app.models.product import Product
from app.models.sales_order import (
    SalesOrder,
    SalesOrderItem,
    SalesOrderStatus,
)
from app.models.inventory import Inventory
from app.models.stock_movement import StockMovement, MovementType
from app.schemas.sales_order import (
    SalesOrderCreate,
    SalesOrderResponse,
    SalesOrderDispatchRequest,
)

router = APIRouter(prefix="/sales-orders", tags=["Sales Orders"])


def generate_so_number():
    return f"SO-{datetime.utcnow():%Y%m%d%H%M%S}-{secrets.token_hex(3).upper()}"


def load_order(db: Session, order_id: int):
    statement = (
        select(SalesOrder)
        .options(selectinload(SalesOrder.items))
        .where(SalesOrder.id == order_id)
    )
    return db.execute(statement).scalar_one_or_none()


@router.post("/", response_model=SalesOrderResponse, status_code=201)
def create_sales_order(
    request: SalesOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)
    ),
):
    customer = db.get(Customer, request.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if hasattr(customer, "is_active") and not customer.is_active:
        raise HTTPException(status_code=400, detail="Customer is inactive")

    warehouse = db.get(Warehouse, request.warehouse_id)
    if not warehouse or not warehouse.is_active:
        raise HTTPException(status_code=400, detail="Active warehouse not found")

    order = SalesOrder(
        so_number=generate_so_number(),
        customer_id=request.customer_id,
        warehouse_id=request.warehouse_id,
        subtotal=Decimal("0"),
        tax_amount=request.tax_amount,
        grand_total=Decimal("0"),
        status=SalesOrderStatus.DRAFT,
        created_by=current_user.id,
    )

    subtotal = Decimal("0")

    try:
        for item_request in request.items:
            product = db.get(Product, item_request.product_id)

            if not product or not product.is_active:
                raise HTTPException(
                    status_code=400,
                    detail=f"Product {item_request.product_id} is not active or does not exist",
                )

            # Use the product's selling price as the order price.
            unit_price = Decimal(str(product.selling_price))
            line_total = (item_request.quantity * unit_price).quantize(
                Decimal("0.01")
            )
            subtotal += line_total

            order.items.append(
                SalesOrderItem(
                    product_id=product.id,
                    quantity=item_request.quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                )
            )

        order.subtotal = subtotal.quantize(Decimal("0.01"))
        order.grand_total = (
            order.subtotal + request.tax_amount
        ).quantize(Decimal("0.01"))

        db.add(order)
        db.commit()
        return load_order(db, order.id)

    except Exception:
        db.rollback()
        raise


@router.get("/", response_model=list[SalesOrderResponse])
def list_sales_orders(
    status: SalesOrderStatus | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(SalesOrder).options(selectinload(SalesOrder.items))

    # Warehouse Staff can only view orders for assigned warehouses.
    if current_user.role == UserRole.WAREHOUSE_STAFF:
        statement = statement.where(
            SalesOrder.warehouse_id == current_user.warehouse_id
        )

    if status:
        statement = statement.where(SalesOrder.status == status)

    statement = statement.order_by(SalesOrder.id.desc()).offset(skip).limit(limit)
    return db.execute(statement).scalars().all()


@router.get("/{order_id}", response_model=SalesOrderResponse)
def get_sales_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = load_order(db, order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")

    if (
        current_user.role == UserRole.WAREHOUSE_STAFF
        and order.warehouse_id != current_user.warehouse_id
    ):
        raise HTTPException(status_code=403, detail="Not allowed for this warehouse")

    return order


@router.patch("/{order_id}/confirm", response_model=SalesOrderResponse)
def confirm_sales_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)
    ),
):
    order = db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == order_id)
        .with_for_update()
    ).scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")

    if order.status != SalesOrderStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only draft orders can be confirmed")

    order.status = SalesOrderStatus.CONFIRMED
    db.commit()
    return load_order(db, order_id)


@router.patch("/{order_id}/dispatch", response_model=SalesOrderResponse)
def dispatch_sales_order(
    order_id: int,
    request: SalesOrderDispatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER, UserRole.WAREHOUSE_STAFF)
    ),
):
    order = db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == order_id)
        .with_for_update()
    ).scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")

    if (
        current_user.role == UserRole.WAREHOUSE_STAFF
        and order.warehouse_id != current_user.warehouse_id
    ):
        raise HTTPException(status_code=403, detail="Not allowed for this warehouse")

    if order.status not in (SalesOrderStatus.CONFIRMED, SalesOrderStatus.PACKED):
        raise HTTPException(
            status_code=400,
            detail="Only confirmed or packed orders can be dispatched",
        )

    try:
        # Lock and validate every stock record before changing any quantity.
        locked_inventory = []
        for item in order.items:
            inventory = db.execute(
                select(Inventory)
                .where(
                    Inventory.product_id == item.product_id,
                    Inventory.warehouse_id == order.warehouse_id,
                )
                .with_for_update()
            ).scalar_one_or_none()

            if not inventory:
                raise HTTPException(
                    status_code=400,
                    detail=f"No inventory record for product {item.product_id}",
                )

            available = inventory.quantity_on_hand - inventory.quantity_reserved
            if available < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient available stock for product {item.product_id}",
                )

            locked_inventory.append((item, inventory))

        # Deduct stock only after all items pass validation.
        for item, inventory in locked_inventory:
            inventory.quantity_on_hand -= item.quantity

            db.add(
                StockMovement(
                    product_id=item.product_id,
                    warehouse_id=order.warehouse_id,
                    movement_type=MovementType.SALE_DISPATCH,
                    quantity=item.quantity,
                    reference_id=order.id,
                    balance_after=inventory.quantity_on_hand,
                    performed_by=current_user.id,
                )
            )

        order.status = SalesOrderStatus.DISPATCHED
        order.courier = request.courier
        order.tracking_number = request.tracking_number
        order.dispatched_at = datetime.utcnow()

        db.commit()
        return load_order(db, order_id)

    except Exception:
        db.rollback()
        raise


@router.patch("/{order_id}/deliver", response_model=SalesOrderResponse)
def deliver_sales_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)
    ),
):
    order = db.get(SalesOrder, order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")

    if order.status != SalesOrderStatus.DISPATCHED:
        raise HTTPException(
            status_code=400,
            detail="Only dispatched orders can be marked delivered",
        )

    order.status = SalesOrderStatus.DELIVERED
    order.delivered_at = datetime.utcnow()
    db.commit()
    return load_order(db, order_id)
