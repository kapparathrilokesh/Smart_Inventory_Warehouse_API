from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.database import get_db
from app.models.category import Category
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.user import User, UserRole
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)
    ),
):
    if db.query(Product).filter(Product.sku == data.sku).first():
        raise HTTPException(status_code=409, detail="SKU already exists")

    if data.barcode and db.query(Product).filter(Product.barcode == data.barcode).first():
        raise HTTPException(status_code=409, detail="Barcode already exists")

    category = db.query(Category).filter(
        Category.id == data.category_id,
        Category.is_active.is_(True),
    ).first()
    if not category:
        raise HTTPException(status_code=400, detail="Active category not found")

    if data.preferred_supplier_id is not None:
        supplier = db.query(Supplier).filter(
            Supplier.id == data.preferred_supplier_id,
            Supplier.is_active.is_(True),
        ).first()
        if not supplier:
            raise HTTPException(status_code=400, detail="Active supplier not found")

    product = Product(
        **data.model_dump(),
        created_by=current_user.id,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/", response_model=list[ProductResponse])
def list_products(
    search: str | None = None,
    category_id: int | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Product).filter(Product.is_active.is_(True))

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            Product.name.like(term) | Product.sku.like(term)
        )

    if category_id is not None:
        query = query.filter(Product.category_id == category_id)

    return query.order_by(Product.id).offset(skip).limit(limit).all()


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.is_active.is_(True),
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Active product not found")

    return product


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)
    ),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    updates = data.model_dump(exclude_unset=True)

    new_cost = updates.get("cost_price", product.cost_price)
    new_selling = updates.get("selling_price", product.selling_price)
    if new_selling < new_cost:
        raise HTTPException(
            status_code=422,
            detail="Selling price must be greater than or equal to cost price",
        )

    if "barcode" in updates and updates["barcode"] is not None:
        duplicate = db.query(Product).filter(
            Product.barcode == updates["barcode"],
            Product.id != product_id,
        ).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="Barcode already exists")

    if "category_id" in updates:
        category = db.query(Category).filter(
            Category.id == updates["category_id"],
            Category.is_active.is_(True),
        ).first()
        if not category:
            raise HTTPException(status_code=400, detail="Active category not found")

    if "preferred_supplier_id" in updates and updates["preferred_supplier_id"] is not None:
        supplier = db.query(Supplier).filter(
            Supplier.id == updates["preferred_supplier_id"],
            Supplier.is_active.is_(True),
        ).first()
        if not supplier:
            raise HTTPException(status_code=400, detail="Active supplier not found")

    if updates.get("is_active") is False:
        stock_exists = db.query(Inventory).filter(
            Inventory.product_id == product_id,
            Inventory.quantity_on_hand > 0,
        ).first()
        if stock_exists:
            raise HTTPException(
                status_code=409,
                detail="Cannot deactivate a product that has stock",
            )

    for field, value in updates.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", response_model=ProductResponse)
def deactivate_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    stock_exists = db.query(Inventory).filter(
        Inventory.product_id == product_id,
        Inventory.quantity_on_hand > 0,
    ).first()

    if stock_exists:
        raise HTTPException(
            status_code=409,
            detail="Cannot deactivate a product that has stock",
        )

    product.is_active = False
    db.commit()
    db.refresh(product)
    return product
