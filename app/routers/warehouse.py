from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.warehouse import Warehouse
from app.models.inventory import Inventory
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseUpdate,
    WarehouseResponse,
)

router = APIRouter(prefix="/warehouses", tags=["Warehouses"])


@router.post(
    "/",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_warehouse(
    data: WarehouseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    existing = db.query(Warehouse).filter(
        Warehouse.warehouse_code == data.warehouse_code
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Warehouse code already exists",
        )

    if data.manager_id is not None:
        manager = db.query(User).filter(
            User.id == data.manager_id,
            User.is_active == True,
        ).first()

        if not manager:
            raise HTTPException(status_code=404, detail="Active manager user not found")

        if manager.role not in (
            UserRole.ADMIN,
            UserRole.INVENTORY_MANAGER,
        ):
            raise HTTPException(
                status_code=400,
                detail="Warehouse manager must be an Admin or Inventory Manager",
            )

    warehouse = Warehouse(
        warehouse_code=data.warehouse_code,
        name=data.name,
        city=data.city,
        address=data.address,
        capacity=data.capacity,
        manager_id=data.manager_id,
        created_by=current_user.id,
    )

    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse


@router.get("/", response_model=list[WarehouseResponse])
def list_warehouses(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Warehouse).filter(Warehouse.is_active == True)

    if current_user.role == UserRole.WAREHOUSE_STAFF:
        if current_user.warehouse_id is None:
            return []
        query = query.filter(Warehouse.id == current_user.warehouse_id)

    return query.order_by(Warehouse.id).offset(skip).limit(limit).all()


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
def get_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    warehouse = db.query(Warehouse).filter(
        Warehouse.id == warehouse_id,
        Warehouse.is_active == True,
    ).first()

    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    if (
        current_user.role == UserRole.WAREHOUSE_STAFF
        and current_user.warehouse_id != warehouse.id
    ):
        raise HTTPException(status_code=403, detail="Access denied to this warehouse")

    return warehouse


@router.patch("/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(
    warehouse_id: int,
    data: WarehouseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)
    ),
):
    warehouse = db.query(Warehouse).filter(
        Warehouse.id == warehouse_id,
        Warehouse.is_active == True,
    ).first()

    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    updates = data.model_dump(exclude_unset=True)

    if "warehouse_code" in updates and updates["warehouse_code"] is not None:
        duplicate = db.query(Warehouse).filter(
            Warehouse.warehouse_code == updates["warehouse_code"],
            Warehouse.id != warehouse_id,
        ).first()

        if duplicate:
            raise HTTPException(status_code=409, detail="Warehouse code already exists")

    if "manager_id" in updates and updates["manager_id"] is not None:
        manager = db.query(User).filter(
            User.id == updates["manager_id"],
            User.is_active == True,
        ).first()

        if not manager:
            raise HTTPException(status_code=404, detail="Active manager user not found")

        if manager.role not in (UserRole.ADMIN, UserRole.INVENTORY_MANAGER):
            raise HTTPException(
                status_code=400,
                detail="Warehouse manager must be an Admin or Inventory Manager",
            )

    if updates.get("is_active") is False:
        stock_exists = db.query(Inventory).filter(
            Inventory.warehouse_id == warehouse_id,
            (
                (Inventory.quantity_on_hand > 0)
                | (Inventory.quantity_reserved > 0)
            ),
        ).first()

        if stock_exists:
            raise HTTPException(
                status_code=400,
                detail="Cannot deactivate a warehouse while stock is present",
            )

    for field, value in updates.items():
        setattr(warehouse, field, value)

    db.commit()
    db.refresh(warehouse)
    return warehouse


@router.delete("/{warehouse_id}")
def deactivate_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    warehouse = db.query(Warehouse).filter(
        Warehouse.id == warehouse_id,
        Warehouse.is_active == True,
    ).first()

    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    stock_exists = db.query(Inventory).filter(
        Inventory.warehouse_id == warehouse_id,
        (
            (Inventory.quantity_on_hand > 0)
            | (Inventory.quantity_reserved > 0)
        ),
    ).first()

    if stock_exists:
        raise HTTPException(
            status_code=400,
            detail="Cannot deactivate a warehouse while stock is present",
        )

    warehouse.is_active = False
    db.commit()

    return {"message": "Warehouse deactivated successfully"}