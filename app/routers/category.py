from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.database import get_db
from app.models.category import Category
from app.models.product import Product
from app.models.user import User, UserRole
from app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)
    ),
):
    name = data.name.strip()

    if db.query(Category).filter(Category.name == name).first():
        raise HTTPException(status_code=409, detail="Category name already exists")

    category = Category(
        name=name,
        description=data.description,
        created_by=current_user.id,
    )

    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("/", response_model=list[CategoryResponse])
def list_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Category)
        .order_by(Category.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    category = db.query(Category).filter(Category.id == category_id).first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    return category


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER)
    ),
):
    category = db.query(Category).filter(Category.id == category_id).first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    updates = data.model_dump(exclude_unset=True)

    if "name" in updates and updates["name"] is not None:
        updates["name"] = updates["name"].strip()

        duplicate = db.query(Category).filter(
            Category.name == updates["name"],
            Category.id != category_id,
        ).first()

        if duplicate:
            raise HTTPException(status_code=409, detail="Category name already exists")

    if updates.get("is_active") is False:
        active_products = db.query(Product).filter(
            Product.category_id == category_id,
            Product.is_active.is_(True),
        ).count()

        if active_products:
            raise HTTPException(
                status_code=409,
                detail="Cannot deactivate a category with active products",
            )

    for field, value in updates.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    category = db.query(Category).filter(Category.id == category_id).first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    active_products = db.query(Product).filter(
        Product.category_id == category_id,
        Product.is_active.is_(True),
    ).count()

    if active_products:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a category with active products",
        )

    db.delete(category)
    db.commit()
    return None
