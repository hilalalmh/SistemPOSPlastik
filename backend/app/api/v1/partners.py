from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.api.pagination import Pagination, pagination_params
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.partner import Customer, Supplier
from app.models.user import User
from app.permissions import CUSTOMER_READ, CUSTOMER_UPDATE, SUPPLIER_READ, SUPPLIER_UPDATE
from app.schemas.audit import CustomerCreate, CustomerOut, SupplierCreate, SupplierOut
from app.services import audit

router = APIRouter(tags=["partners"])


@router.get("/suppliers")
def list_suppliers(
    q: str | None = None,
    page: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(SUPPLIER_READ)),
):
    stmt = select(Supplier)
    if q:
        stmt = stmt.where(Supplier.name.ilike(f"%{q}%"))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = (
        db.execute(stmt.order_by(Supplier.name).offset(page.offset).limit(page.page_size))
        .scalars()
        .all()
    )
    return {
        "data": [SupplierOut.model_validate(s) for s in rows],
        "page": page.page,
        "page_size": page.page_size,
        "total": total,
    }


@router.post("/suppliers", response_model=SupplierOut, status_code=201)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(SUPPLIER_UPDATE)),
):
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    audit.log_action(db, action="supplier.create", entity_type="supplier", actor_id=user.id)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.patch("/suppliers/{supplier_id}", response_model=SupplierOut)
def update_supplier(
    supplier_id: UUID,
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(SUPPLIER_UPDATE)),
):
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise NotFoundError("Supplier tidak ditemukan.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, key, value)
    audit.log_action(
        db,
        action="supplier.update",
        entity_type="supplier",
        entity_id=supplier.id,
        actor_id=user.id,
    )
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/customers")
def list_customers(
    q: str | None = None,
    page: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(CUSTOMER_READ)),
):
    stmt = select(Customer)
    if q:
        stmt = stmt.where(Customer.name.ilike(f"%{q}%"))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = (
        db.execute(stmt.order_by(Customer.name).offset(page.offset).limit(page.page_size))
        .scalars()
        .all()
    )
    return {
        "data": [CustomerOut.model_validate(c) for c in rows],
        "page": page.page,
        "page_size": page.page_size,
        "total": total,
    }


@router.post("/customers", response_model=CustomerOut, status_code=201)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(CUSTOMER_UPDATE)),
):
    customer = Customer(**payload.model_dump())
    db.add(customer)
    audit.log_action(db, action="customer.create", entity_type="customer", actor_id=user.id)
    db.commit()
    db.refresh(customer)
    return customer


@router.patch("/customers/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: UUID,
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(CUSTOMER_UPDATE)),
):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Pelanggan tidak ditemukan.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer
