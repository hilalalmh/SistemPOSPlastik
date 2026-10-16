from fastapi import APIRouter

from app.api.v1 import (
    audit,
    auth,
    catalog,
    expenses,
    inventory,
    labels,
    partners,
    products,
    purchases,
    reports,
    returns,
    sales,
    users,
)
from app.api.v1 import (
    settings as settings_router,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(settings_router.router)
api_router.include_router(products.router)
api_router.include_router(catalog.router)
api_router.include_router(labels.router)
api_router.include_router(inventory.router)
api_router.include_router(expenses.router)
api_router.include_router(purchases.router)
api_router.include_router(sales.router)
api_router.include_router(returns.router)
api_router.include_router(partners.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
