
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("/", response_model=CustomerResponse, status_code=201)
def create_customer(
    request: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)
    ),
):
    existing = db.execute(
        select(Customer).where(
            (Customer.customer_code == request.customer_code)
            | (Customer.email == str(request.email))
        )
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Customer code or email already exists",
        )

    customer = Customer(
        customer_code=request.customer_code,
        name=request.name,
        email=str(request.email),
        phone=request.phone,
        address=request.address,
        credit_limit=request.credit_limit,
        created_by=current_user.id,
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/", response_model=list[CustomerResponse])
def list_customers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Customer)
        .where(Customer.is_active.is_(True))
        .order_by(Customer.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return db.execute(statement).scalars().all()


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = db.get(Customer, customer_id)

    if not customer or not customer.is_active:
        raise HTTPException(status_code=404, detail="Active customer not found")

    return customer


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    request: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)
    ),
):
    customer = db.get(Customer, customer_id)

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    changes = request.model_dump(exclude_unset=True)

    for field in ("email",):
        if field in changes and changes[field] is not None:
            changes[field] = str(changes[field])

    for field in ("customer_code", "email"):
        if field in changes and changes[field] is not None:
            duplicate = db.execute(
                select(Customer).where(
                    getattr(Customer, field) == changes[field],
                    Customer.id != customer_id,
                )
            ).scalar_one_or_none()

            if duplicate:
                raise HTTPException(
                    status_code=409,
                    detail=f"{field} already exists",
                )

    for field, value in changes.items():
        setattr(customer, field, value)

    db.commit()
    db.refresh(customer)
    return customer
