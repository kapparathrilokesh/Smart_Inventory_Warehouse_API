
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.inventory import Inventory
from app.models.stock_movement import StockMovement, MovementType
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.schemas.inventory import (
    InventoryResponse,
    StockMovementResponse,
    StockReceiptRequest,
)

router = APIRouter(prefix="/inventory", tags=["Inventory"])


def check_warehouse_access(current_user: User, warehouse_id: int):
    if (
        current_user.role == UserRole.WAREHOUSE_STAFF
        and current_user.warehouse_id != warehouse_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Access denied to this warehouse",
        )


@router.get("/", response_model=list[InventoryResponse])
def list_inventory(
    product_id: int | None = Query(default=None, ge=1),
    warehouse_id: int | None = Query(default=None, ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Inventory)

    if current_user.role == UserRole.WAREHOUSE_STAFF:
        if current_user.warehouse_id is None:
            return []
        query = query.filter(
            Inventory.warehouse_id == current_user.warehouse_id
        )

    if product_id is not None:
        query = query.filter(Inventory.product_id == product_id)

    if warehouse_id is not None:
        check_warehouse_access(current_user, warehouse_id)
        query = query.filter(Inventory.warehouse_id == warehouse_id)

    records = (
        query.order_by(Inventory.id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        InventoryResponse(
            id=item.id,
            product_id=item.product_id,
            warehouse_id=item.warehouse_id,
            quantity_on_hand=item.quantity_on_hand,
            quantity_reserved=item.quantity_reserved,
            available_quantity=(
                item.quantity_on_hand - item.quantity_reserved
            ),
        )
        for item in records
    ]


@router.get("/movements", response_model=list[StockMovementResponse])
def list_stock_movements(
    product_id: int | None = Query(default=None, ge=1),
    warehouse_id: int | None = Query(default=None, ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(StockMovement)

    if current_user.role == UserRole.WAREHOUSE_STAFF:
        if current_user.warehouse_id is None:
            return []
        query = query.filter(
            StockMovement.warehouse_id == current_user.warehouse_id
        )

    if product_id is not None:
        query = query.filter(StockMovement.product_id == product_id)

    if warehouse_id is not None:
        check_warehouse_access(current_user, warehouse_id)
        query = query.filter(
            StockMovement.warehouse_id == warehouse_id
        )

    return (
        query.order_by(StockMovement.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get(
    "/{product_id}/{warehouse_id}",
    response_model=InventoryResponse,
)
def get_product_inventory(
    product_id: int,
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_warehouse_access(current_user, warehouse_id)

    record = db.query(Inventory).filter(
        Inventory.product_id == product_id,
        Inventory.warehouse_id == warehouse_id,
    ).first()

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Inventory record not found for this product and warehouse",
        )

    return InventoryResponse(
        id=record.id,
        product_id=record.product_id,
        warehouse_id=record.warehouse_id,
        quantity_on_hand=record.quantity_on_hand,
        quantity_reserved=record.quantity_reserved,
        available_quantity=(
            record.quantity_on_hand - record.quantity_reserved
        ),
    )


@router.post(
    "/receive",
    response_model=InventoryResponse,
    status_code=201,
)
def receive_stock(
    request: StockReceiptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (
        UserRole.ADMIN,
        UserRole.INVENTORY_MANAGER,
    ):
        raise HTTPException(
            status_code=403,
            detail="Only Admin or Inventory Manager can receive stock",
        )

    product = db.query(Product).filter(
        Product.id == request.product_id,
        Product.is_active.is_(True),
    ).first()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Active product not found",
        )

    warehouse = db.query(Warehouse).filter(
        Warehouse.id == request.warehouse_id,
        Warehouse.is_active.is_(True),
    ).first()

    if warehouse is None:
        raise HTTPException(
            status_code=404,
            detail="Active warehouse not found",
        )

    try:
        inventory = (
            db.query(Inventory)
            .filter(
                Inventory.product_id == request.product_id,
                Inventory.warehouse_id == request.warehouse_id,
            )
            .with_for_update()
            .first()
        )

        if inventory is None:
            inventory = Inventory(
                product_id=request.product_id,
                warehouse_id=request.warehouse_id,
                quantity_on_hand=Decimal("0"),
                quantity_reserved=Decimal("0"),
                created_by=current_user.id,
            )
            db.add(inventory)
            db.flush()

        inventory.quantity_on_hand = (
            inventory.quantity_on_hand + request.quantity
        )

        movement = StockMovement(
            product_id=request.product_id,
            warehouse_id=request.warehouse_id,
            movement_type=MovementType.PURCHASE_RECEIPT,
            quantity=request.quantity,
            reference_id=None,
            balance_after=inventory.quantity_on_hand,
            performed_by=current_user.id,
        )

        db.add(movement)
        db.flush()

        response = InventoryResponse(
            id=inventory.id,
            product_id=inventory.product_id,
            warehouse_id=inventory.warehouse_id,
            quantity_on_hand=inventory.quantity_on_hand,
            quantity_reserved=inventory.quantity_reserved,
            available_quantity=(
                inventory.quantity_on_hand
                - inventory.quantity_reserved
            ),
        )

        db.commit()
        return response

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not record stock; please retry",
        )
    except Exception:
        db.rollback()
        raise
