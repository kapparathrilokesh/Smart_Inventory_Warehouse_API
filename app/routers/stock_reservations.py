from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.inventory import Inventory
from app.models.stock_reservation import (
    StockReservation,
    ReservationStatus,
)
from app.models.audit_log import AuditLog
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.sales_order import SalesOrder
from app.schemas.stock_reservation import (
    StockReservationCreate,
    StockReservationResponse,
)

router = APIRouter(
    prefix="/stock-reservations",
    tags=["Stock Reservations"],
)


@router.post(
    "/",
    response_model=StockReservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_reservation(
    data: StockReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)
    ),
):
    product = db.query(Product).filter(
        Product.id == data.product_id,
        Product.is_active == True,
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Active product not found",
        )

    warehouse = db.query(Warehouse).filter(
        Warehouse.id == data.warehouse_id,
        Warehouse.is_active == True,
    ).first()

    if not warehouse:
        raise HTTPException(
            status_code=404,
            detail="Active warehouse not found",
        )

    if data.sales_order_id is not None:
        order = db.query(SalesOrder).filter(
            SalesOrder.id == data.sales_order_id
        ).first()

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Sales order not found",
            )

        if order.warehouse_id != data.warehouse_id:
            raise HTTPException(
                status_code=400,
                detail="Sales order belongs to a different warehouse",
            )

    try:
        inventory = (
            db.query(Inventory)
            .filter(
                Inventory.product_id == data.product_id,
                Inventory.warehouse_id == data.warehouse_id,
            )
            .with_for_update()
            .first()
        )

        if not inventory:
            raise HTTPException(
                status_code=404,
                detail="Inventory record not found",
            )

        available = (
            inventory.quantity_on_hand
            - inventory.quantity_reserved
        )

        if data.quantity > available:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock. Available quantity: {available}",
            )

        inventory.quantity_reserved += data.quantity

        reservation = StockReservation(
            product_id=data.product_id,
            warehouse_id=data.warehouse_id,
            sales_order_id=data.sales_order_id,
            quantity=data.quantity,
            status=ReservationStatus.ACTIVE,
            reserved_by=current_user.id,
        )

        db.add(reservation)
        db.flush()

        db.add(
            AuditLog(
                user_id=current_user.id,
                action="CREATE",
                entity_type="StockReservation",
                entity_id=reservation.id,
                details=(
                    f"Reserved quantity {data.quantity} "
                    f"for product {data.product_id} "
                    f"in warehouse {data.warehouse_id}"
                ),
            )
        )

        db.commit()
        db.refresh(reservation)
        return reservation

    except Exception:
        db.rollback()
        raise


@router.get(
    "/",
    response_model=list[StockReservationResponse],
)
def list_reservations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(StockReservation)

    if current_user.role == UserRole.WAREHOUSE_STAFF:
        if not current_user.warehouse_id:
            return []

        query = query.filter(
            StockReservation.warehouse_id
            == current_user.warehouse_id
        )

    return query.order_by(
        StockReservation.id.desc()
    ).all()


@router.patch(
    "/{reservation_id}/release",
    response_model=StockReservationResponse,
)
def release_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.INVENTORY_MANAGER,
            UserRole.WAREHOUSE_STAFF,
        )
    ),
):
    try:
        reservation = (
            db.query(StockReservation)
            .filter(StockReservation.id == reservation_id)
            .with_for_update()
            .first()
        )

        if not reservation:
            raise HTTPException(
                status_code=404,
                detail="Reservation not found",
            )

        if current_user.role == UserRole.WAREHOUSE_STAFF:
            if (
                not current_user.warehouse_id
                or current_user.warehouse_id != reservation.warehouse_id
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Not allowed for this warehouse",
                )

        if reservation.status != ReservationStatus.ACTIVE:
            raise HTTPException(
                status_code=400,
                detail="Reservation is not active",
            )

        inventory = (
            db.query(Inventory)
            .filter(
                Inventory.product_id == reservation.product_id,
                Inventory.warehouse_id == reservation.warehouse_id,
            )
            .with_for_update()
            .first()
        )

        if not inventory:
            raise HTTPException(
                status_code=404,
                detail="Inventory record not found",
            )

        if inventory.quantity_reserved < reservation.quantity:
            raise HTTPException(
                status_code=409,
                detail="Reserved stock is inconsistent",
            )

        inventory.quantity_reserved -= reservation.quantity
        reservation.status = ReservationStatus.RELEASED

        db.add(
            AuditLog(
                user_id=current_user.id,
                action="RELEASE",
                entity_type="StockReservation",
                entity_id=reservation.id,
                details=(
                    f"Released quantity {reservation.quantity} "
                    f"for product {reservation.product_id} "
                    f"in warehouse {reservation.warehouse_id}"
                ),
            )
        )

        db.commit()
        db.refresh(reservation)
        return reservation

    except Exception:
        db.rollback()
        raise