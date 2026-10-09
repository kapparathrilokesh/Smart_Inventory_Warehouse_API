
from datetime import datetime
from decimal import Decimal
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.supplier import Supplier
from app.models.warehouse import Warehouse
from app.models.product import Product
from app.models.purchase_order import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
)
from app.models.inventory import Inventory
from app.models.stock_movement import StockMovement, MovementType
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    PurchaseOrderReceive,
)

router = APIRouter(prefix="/purchase-orders", tags=["Purchase Orders"])


def generate_po_number():
    return f"PO-{datetime.utcnow():%Y%m%d%H%M%S}-{secrets.token_hex(3).upper()}"


@router.post(
    "/",
    response_model=PurchaseOrderResponse,
    status_code=201,
)
def create_purchase_order(
    request: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)
    ),
):
    supplier = db.query(Supplier).filter(
        Supplier.id == request.supplier_id,
        Supplier.is_active.is_(True),
    ).first()

    if supplier is None:
        raise HTTPException(status_code=404, detail="Active supplier not found")

    warehouse = db.query(Warehouse).filter(
        Warehouse.id == request.warehouse_id,
        Warehouse.is_active.is_(True),
    ).first()

    if warehouse is None:
        raise HTTPException(status_code=404, detail="Active warehouse not found")

    try:
        total_amount = Decimal("0")
        order = PurchaseOrder(
            po_number=generate_po_number(),
            supplier_id=request.supplier_id,
            warehouse_id=request.warehouse_id,
            expected_date=request.expected_date,
            total_amount=Decimal("0"),
            status=PurchaseOrderStatus.DRAFT,
            created_by=current_user.id,
        )
        db.add(order)
        db.flush()

        for item_data in request.items:
            product = db.query(Product).filter(
                Product.id == item_data.product_id,
                Product.is_active.is_(True),
            ).first()

            if product is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Active product {item_data.product_id} not found",
                )

            line_total = (
                item_data.ordered_quantity * item_data.unit_cost
            ).quantize(Decimal("0.01"))

            order_item = PurchaseOrderItem(
                purchase_order_id=order.id,
                product_id=item_data.product_id,
                ordered_quantity=item_data.ordered_quantity,
                received_quantity=Decimal("0"),
                unit_cost=item_data.unit_cost,
                line_total=line_total,
            )
            db.add(order_item)
            total_amount += line_total

        order.total_amount = total_amount
        db.commit()
        db.refresh(order)
        return order

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


@router.get("/", response_model=list[PurchaseOrderResponse])
def list_purchase_orders(
    status: PurchaseOrderStatus | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(PurchaseOrder)

    if status is not None:
        query = query.filter(PurchaseOrder.status == status)

    return (
        query.order_by(PurchaseOrder.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{order_id}", response_model=PurchaseOrderResponse)
def get_purchase_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.query(PurchaseOrder).filter(
        PurchaseOrder.id == order_id
    ).first()

    if order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    return order


@router.patch(
    "/{order_id}/approve",
    response_model=PurchaseOrderResponse,
)
def approve_purchase_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)
    ),
):
    order = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.id == order_id)
        .with_for_update()
        .first()
    )

    if order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if order.status != PurchaseOrderStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Only draft purchase orders can be approved",
        )

    order.status = PurchaseOrderStatus.APPROVED
    db.commit()
    db.refresh(order)
    return order


@router.post(
    "/{order_id}/receive",
    response_model=PurchaseOrderResponse,
)
def receive_purchase_order(
    order_id: int,
    request: PurchaseOrderReceive,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)
    ),
):
    order = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.id == order_id)
        .with_for_update()
        .first()
    )

    if order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if order.status not in (
        PurchaseOrderStatus.APPROVED,
        PurchaseOrderStatus.PARTIALLY_RECEIVED,
    ):
        raise HTTPException(
            status_code=400,
            detail="Only approved or partially received orders can receive stock",
        )

    warehouse = db.query(Warehouse).filter(
        Warehouse.id == order.warehouse_id,
        Warehouse.is_active.is_(True),
    ).first()

    if warehouse is None:
        raise HTTPException(status_code=400, detail="Order warehouse is inactive")

    try:
        for receipt in request.items:
            item = (
                db.query(PurchaseOrderItem)
                .filter(
                    PurchaseOrderItem.id == receipt.item_id,
                    PurchaseOrderItem.purchase_order_id == order.id,
                )
                .with_for_update()
                .first()
            )

            if item is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Purchase order item {receipt.item_id} not found",
                )

            remaining = item.ordered_quantity - item.received_quantity

            if receipt.received_quantity > remaining:
                raise HTTPException(
                    status_code=400,
                    detail=f"Received quantity exceeds remaining quantity for item {item.id}",
                )

            inventory = (
                db.query(Inventory)
                .filter(
                    Inventory.product_id == item.product_id,
                    Inventory.warehouse_id == order.warehouse_id,
                )
                .with_for_update()
                .first()
            )

            if inventory is None:
                inventory = Inventory(
                    product_id=item.product_id,
                    warehouse_id=order.warehouse_id,
                    quantity_on_hand=Decimal("0"),
                    quantity_reserved=Decimal("0"),
                    created_by=current_user.id,
                )
                db.add(inventory)
                db.flush()

            inventory.quantity_on_hand += receipt.received_quantity
            item.received_quantity += receipt.received_quantity

            db.add(
                StockMovement(
                    product_id=item.product_id,
                    warehouse_id=order.warehouse_id,
                    movement_type=MovementType.PURCHASE_RECEIPT,
                    quantity=receipt.received_quantity,
                    reference_id=order.id,
                    balance_after=inventory.quantity_on_hand,
                    performed_by=current_user.id,
                )
            )

        all_received = all(
            item.received_quantity >= item.ordered_quantity
            for item in order.items
        )

        any_received = any(
            item.received_quantity > 0 for item in order.items
        )

        if all_received:
            order.status = PurchaseOrderStatus.RECEIVED
            order.received_at = datetime.utcnow()
        elif any_received:
            order.status = PurchaseOrderStatus.PARTIALLY_RECEIVED

        db.commit()
        db.refresh(order)
        return order

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


@router.patch(
    "/{order_id}/cancel",
    response_model=PurchaseOrderResponse,
)
def cancel_purchase_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)
    ),
):
    order = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.id == order_id)
        .with_for_update()
        .first()
    )

    if order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if order.status not in (
        PurchaseOrderStatus.DRAFT,
        PurchaseOrderStatus.APPROVED,
    ):
        raise HTTPException(
            status_code=400,
            detail="Only draft or approved orders without receipts can be cancelled",
        )

    if any(item.received_quantity > 0 for item in order.items):
        raise HTTPException(
            status_code=400,
            detail="A purchase order with received stock cannot be cancelled",
        )

    order.status = PurchaseOrderStatus.CANCELLED
    db.commit()
    db.refresh(order)
    return order
