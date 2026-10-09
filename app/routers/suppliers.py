from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.supplier import Supplier

from app.schemas.suppliers import (
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
)

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.post("/", response_model=SupplierResponse, status_code=201)
def create_supplier(
    request: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)
    ),
):
    if db.query(Supplier).filter(
        Supplier.supplier_code == request.supplier_code
    ).first():
        raise HTTPException(
            status_code=409, detail="Supplier code already exists"
        )

    if db.query(Supplier).filter(
        Supplier.email == str(request.email)
    ).first():
        raise HTTPException(
            status_code=409, detail="Supplier email already exists"
        )

    if request.gst_number and db.query(Supplier).filter(
        Supplier.gst_number == request.gst_number
    ).first():
        raise HTTPException(
            status_code=409, detail="GST number already exists"
        )

    supplier = Supplier(
        supplier_code=request.supplier_code,
        name=request.name,
        email=str(request.email),
        phone=request.phone,
        gst_number=request.gst_number,
        address=request.address,
        lead_time_days=request.lead_time_days,
        created_by=current_user.id,
    )

    try:
        db.add(supplier)
        db.commit()
        db.refresh(supplier)
        return supplier
    except Exception:
        db.rollback()
        raise


@router.get("/", response_model=list[SupplierResponse])
def list_suppliers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Supplier)
        .filter(Supplier.is_active.is_(True))
        .order_by(Supplier.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.is_active.is_(True),
    ).first()

    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")

    return supplier


@router.patch("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: int,
    request: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)
    ),
):
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id
    ).first()

    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")

    changes = request.model_dump(exclude_unset=True)

    for field in ("supplier_code", "email", "gst_number"):
        value = changes.get(field)
        if value is not None:
            if field == "email":
                value = str(value)
                changes[field] = value

            existing = db.query(Supplier).filter(
                getattr(Supplier, field) == value,
                Supplier.id != supplier_id,
            ).first()

            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"{field.replace('_', ' ').title()} already exists",
                )

    for field, value in changes.items():
        setattr(supplier, field, value)

    try:
        db.commit()
        db.refresh(supplier)
        return supplier
    except Exception:
        db.rollback()
        raise