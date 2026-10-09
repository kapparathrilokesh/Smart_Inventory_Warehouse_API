from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import require_roles
from app.models.user import User, UserRole
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.warehouse import Warehouse

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


@router.get("/low-stock")
def low_stock_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.INVENTORY_MANAGER,
        )
    ),
):
    rows = (
        db.query(Inventory, Product, Warehouse)
        .join(Product, Inventory.product_id == Product.id)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .filter(
            Product.is_active == True,
            Warehouse.is_active == True,
            Inventory.quantity_on_hand - Inventory.quantity_reserved
            <= Product.reorder_level,
        )
        .order_by(
            Inventory.quantity_on_hand - Inventory.quantity_reserved
        )
        .all()
    )

    return [
        {
            "product_id": product.id,
            "product_name": product.name,
            "sku": product.sku,
            "warehouse_id": warehouse.id,
            "warehouse_name": warehouse.name,
            "quantity_on_hand": str(inventory.quantity_on_hand),
            "quantity_reserved": str(inventory.quantity_reserved),
            "available_quantity": str(
                inventory.quantity_on_hand - inventory.quantity_reserved
            ),
            "reorder_level": product.reorder_level,
            "needs_restock": True,
        }
        for inventory, product, warehouse in rows
    ]
