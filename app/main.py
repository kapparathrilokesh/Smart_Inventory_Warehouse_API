from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.category import router as categories_router
from app.routers.product import router as products_router
from app.routers.warehouse import router as warehouses_router
from app.routers.inventory import router as inventory_router
from app.routers.purchase_orders import router as purchase_orders_router
from app.routers.suppliers import router as suppliers_router
from app.routers.sales_orders import router as sales_orders_router
from app.routers.customers import router as customers_router
from app.routers import stock_reservations
from app.routers import reports
from app.routers import audit_logs

app = FastAPI(
    title="Smart Inventory & Warehouse Management API",
    version="1.0.0"
)


app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(products_router)
app.include_router(warehouses_router)
app.include_router(inventory_router)
app.include_router(purchase_orders_router)
app.include_router(suppliers_router)
app.include_router(sales_orders_router)
app.include_router(customers_router)
app.include_router(stock_reservations.router)
app.include_router(reports.router)
app.include_router(audit_logs.router)


@app.get("/")
def root():
    return {
        "message": "Smart Inventory & Warehouse Management API is running"
    }