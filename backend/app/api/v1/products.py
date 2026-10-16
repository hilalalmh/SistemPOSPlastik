from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_permission
from app.api.pagination import Pagination, pagination_params
from app.core.database import get_db
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.product import (
    Category,
    PriceHistory,
    Product,
    ProductPrice,
    ProductUnitConversion,
    ProductVariant,
    Unit,
)
from app.models.user import User
from app.permissions import PRICE_READ, PRICE_UPDATE, PRODUCT_READ, PRODUCT_UPDATE
from app.schemas.product import (
    CategoryCreate,
    CategoryOut,
    ConversionIn,
    ConversionOut,
    PriceCreate,
    PriceOut,
    PriceUpdate,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    UnitCreate,
    UnitOut,
    VariantCreate,
    VariantOut,
    VariantUpdate,
)
from app.services import audit

router = APIRouter(tags=["products"])


# ---------------------------------------------------------------- helpers
def _effective_max(value) -> Decimal:
    return Decimal(value) if value is not None else Decimal("1e18")


def _ranges_overlap(min_a, max_a, min_b, max_b) -> bool:
    return Decimal(min_a) <= _effective_max(max_b) and Decimal(min_b) <= _effective_max(max_a)


def _validate_price_range(
    db: Session, variant_id: UUID, unit_id: UUID, min_qty, max_qty, exclude_id: UUID | None = None
) -> None:
    stmt = select(ProductPrice).where(
        ProductPrice.variant_id == variant_id,
        ProductPrice.unit_id == unit_id,
        ProductPrice.is_active.is_(True),
    )
    if exclude_id is not None:
        stmt = stmt.where(ProductPrice.id != exclude_id)
    for existing in db.execute(stmt).scalars():
        if _ranges_overlap(min_qty, max_qty, existing.min_qty, existing.max_qty):
            raise BusinessRuleError(
                "Rentang kuantitas harga bertabrakan dengan harga lain yang aktif.",
                code="PRICE_RANGE_OVERLAP",
            )


def _record_price_history(
    db: Session, variant_id: UUID, unit_id: UUID, old_price, new_price, user_id: UUID
):
    db.add(
        PriceHistory(
            variant_id=variant_id,
            unit_id=unit_id,
            old_price=old_price,
            new_price=new_price,
            changed_by=user_id,
        )
    )


# ---------------------------------------------------------------- categories
@router.get("/categories", response_model=list[CategoryOut])
def list_categories(
    db: Session = Depends(get_db), _: User = Depends(require_permission(PRODUCT_READ))
):
    return db.execute(select(Category).order_by(Category.name)).scalars().all()


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PRODUCT_UPDATE)),
):
    category = Category(**payload.model_dump())
    db.add(category)
    audit.log_action(db, action="category.create", entity_type="category", actor_id=user.id)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: UUID,
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PRODUCT_UPDATE)),
):
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundError("Kategori tidak ditemukan.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    audit.log_action(
        db,
        action="category.update",
        entity_type="category",
        entity_id=category.id,
        actor_id=user.id,
    )
    db.commit()
    db.refresh(category)
    return category


# --------------------------------------------------------------------- units
@router.get("/units", response_model=list[UnitOut])
def list_units(db: Session = Depends(get_db), _: User = Depends(require_permission(PRODUCT_READ))):
    return db.execute(select(Unit).order_by(Unit.name)).scalars().all()


@router.post("/units", response_model=UnitOut, status_code=201)
def create_unit(
    payload: UnitCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PRODUCT_UPDATE)),
):
    unit = Unit(**payload.model_dump())
    db.add(unit)
    audit.log_action(db, action="unit.create", entity_type="unit", actor_id=user.id)
    db.commit()
    db.refresh(unit)
    return unit


# ------------------------------------------------------------------ products
@router.get("/products")
def list_products(
    q: str | None = None,
    category_id: UUID | None = None,
    is_active: bool | None = None,
    page: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PRODUCT_READ)),
):
    stmt = select(Product)
    if q:
        stmt = stmt.where(Product.name.ilike(f"%{q}%"))
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if is_active is not None:
        stmt = stmt.where(Product.is_active.is_(is_active))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = (
        db.execute(stmt.order_by(Product.name).offset(page.offset).limit(page.page_size))
        .scalars()
        .all()
    )
    return {
        "data": [ProductOut.model_validate(p) for p in rows],
        "page": page.page,
        "page_size": page.page_size,
        "total": total,
    }


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PRODUCT_UPDATE)),
):
    product = Product(**payload.model_dump())
    db.add(product)
    audit.log_action(db, action="product.create", entity_type="product", actor_id=user.id)
    db.commit()
    db.refresh(product)
    return product


@router.get("/products/{product_id}")
def get_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PRODUCT_READ)),
):
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError("Produk tidak ditemukan.")
    variants = (
        db.execute(select(ProductVariant).where(ProductVariant.product_id == product_id))
        .scalars()
        .all()
    )
    data = ProductOut.model_validate(product).model_dump()
    data["variants"] = [VariantOut.model_validate(v).model_dump() for v in variants]
    return data


@router.patch("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PRODUCT_UPDATE)),
):
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError("Produk tidak ditemukan.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    audit.log_action(
        db,
        action="product.update",
        entity_type="product",
        entity_id=product.id,
        actor_id=user.id,
        meta=payload.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(product)
    return product


@router.post("/products/{product_id}/deactivate", response_model=ProductOut)
def deactivate_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PRODUCT_UPDATE)),
):
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError("Produk tidak ditemukan.")
    product.is_active = False
    audit.log_action(
        db,
        action="product.deactivate",
        entity_type="product",
        entity_id=product.id,
        actor_id=user.id,
    )
    db.commit()
    db.refresh(product)
    return product


# ------------------------------------------------------------------- variants
def _variant_out(db: Session, variant: ProductVariant) -> dict:
    data = VariantOut.model_validate(variant).model_dump()
    return data


@router.get("/variants")
def list_variants(
    q: str | None = None,
    product_id: UUID | None = None,
    barcode: str | None = None,
    page: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PRODUCT_READ)),
):
    stmt = select(ProductVariant).options(selectinload(ProductVariant.product))
    if q:
        stmt = stmt.where(
            ProductVariant.sku.ilike(f"%{q}%") | ProductVariant.barcode.ilike(f"%{q}%")
        )
    if product_id:
        stmt = stmt.where(ProductVariant.product_id == product_id)
    if barcode:
        stmt = stmt.where(ProductVariant.barcode == barcode)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = (
        db.execute(stmt.order_by(ProductVariant.sku).offset(page.offset).limit(page.page_size))
        .scalars()
        .all()
    )
    return {
        "data": [VariantOut.model_validate(v) for v in rows],
        "page": page.page,
        "page_size": page.page_size,
        "total": total,
    }


@router.post("/variants", response_model=VariantOut, status_code=201)
def create_variant(
    payload: VariantCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PRODUCT_UPDATE)),
):
    if db.get(Product, payload.product_id) is None:
        raise NotFoundError("Produk tidak ditemukan.")
    existing = db.execute(
        select(ProductVariant).where(ProductVariant.sku == payload.sku)
    ).scalar_one_or_none()
    if existing is not None:
        raise BusinessRuleError("SKU sudah digunakan.", code="SKU_EXISTS")

    variant = ProductVariant(**payload.model_dump(exclude={"conversions", "prices"}))
    db.add(variant)
    db.flush()

    _upsert_conversions(db, variant, payload.conversions)
    for price in payload.prices:
        _validate_price_range(db, variant.id, price.unit_id, price.min_qty, price.max_qty)
        db.add(
            ProductPrice(
                variant_id=variant.id,
                unit_id=price.unit_id,
                min_qty=price.min_qty,
                max_qty=price.max_qty,
                unit_price=price.unit_price,
                valid_from=price.valid_from,
                valid_to=price.valid_to,
            )
        )
    audit.log_action(
        db, action="variant.create", entity_type="variant", entity_id=variant.id, actor_id=user.id
    )
    db.commit()
    db.refresh(variant)
    return variant


def _upsert_conversions(db: Session, variant: ProductVariant, conversions: list[ConversionIn]):
    existing = {
        c.unit_id: c
        for c in db.execute(
            select(ProductUnitConversion).where(ProductUnitConversion.variant_id == variant.id)
        ).scalars()
    }
    for conv in conversions:
        if conv.base_units_per_unit <= 0:
            raise BusinessRuleError("Faktor konversi harus positif.", code="INVALID_CONVERSION")
        current = existing.get(conv.unit_id)
        if current is not None:
            current.base_units_per_unit = conv.base_units_per_unit
            current.is_active = True
        else:
            db.add(
                ProductUnitConversion(
                    variant_id=variant.id,
                    unit_id=conv.unit_id,
                    base_units_per_unit=conv.base_units_per_unit,
                )
            )
    db.flush()


@router.get("/variants/{variant_id}")
def get_variant(
    variant_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PRODUCT_READ)),
):
    variant = db.get(ProductVariant, variant_id)
    if variant is None:
        raise NotFoundError("Varian tidak ditemukan.")
    data = VariantOut.model_validate(variant).model_dump()
    convs = (
        db.execute(
            select(ProductUnitConversion).where(ProductUnitConversion.variant_id == variant_id)
        )
        .scalars()
        .all()
    )
    prices = (
        db.execute(
            select(ProductPrice).where(
                ProductPrice.variant_id == variant_id, ProductPrice.is_active.is_(True)
            )
        )
        .scalars()
        .all()
    )
    data["conversions"] = [ConversionOut.model_validate(c).model_dump() for c in convs]
    data["prices"] = [PriceOut.model_validate(p).model_dump() for p in prices]
    return data


@router.patch("/variants/{variant_id}", response_model=VariantOut)
def update_variant(
    variant_id: UUID,
    payload: VariantUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PRODUCT_UPDATE)),
):
    variant = db.get(ProductVariant, variant_id)
    if variant is None:
        raise NotFoundError("Varian tidak ditemukan.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(variant, key, value)
    audit.log_action(
        db, action="variant.update", entity_type="variant", entity_id=variant.id, actor_id=user.id
    )
    db.commit()
    db.refresh(variant)
    return variant


@router.post("/variants/{variant_id}/deactivate", response_model=VariantOut)
def deactivate_variant(
    variant_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PRODUCT_UPDATE)),
):
    variant = db.get(ProductVariant, variant_id)
    if variant is None:
        raise NotFoundError("Varian tidak ditemukan.")
    variant.is_active = False
    audit.log_action(
        db,
        action="variant.deactivate",
        entity_type="variant",
        entity_id=variant.id,
        actor_id=user.id,
    )
    db.commit()
    db.refresh(variant)
    return variant


@router.get("/variants/{variant_id}/conversions", response_model=list[ConversionOut])
def get_conversions(
    variant_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PRODUCT_READ)),
):
    return (
        db.execute(
            select(ProductUnitConversion).where(ProductUnitConversion.variant_id == variant_id)
        )
        .scalars()
        .all()
    )


@router.put("/variants/{variant_id}/conversions", response_model=list[ConversionOut])
def set_conversions(
    variant_id: UUID,
    payload: list[ConversionIn],
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PRODUCT_UPDATE)),
):
    variant = db.get(ProductVariant, variant_id)
    if variant is None:
        raise NotFoundError("Varian tidak ditemukan.")
    _upsert_conversions(db, variant, payload)
    audit.log_action(
        db,
        action="variant.set_conversions",
        entity_type="variant",
        entity_id=variant.id,
        actor_id=user.id,
    )
    db.commit()
    return (
        db.execute(
            select(ProductUnitConversion).where(ProductUnitConversion.variant_id == variant_id)
        )
        .scalars()
        .all()
    )


# --------------------------------------------------------------------- prices
@router.get("/variants/{variant_id}/prices", response_model=list[PriceOut])
def get_prices(
    variant_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PRICE_READ)),
):
    return (
        db.execute(
            select(ProductPrice)
            .where(ProductPrice.variant_id == variant_id)
            .order_by(ProductPrice.unit_id, ProductPrice.min_qty)
        )
        .scalars()
        .all()
    )


@router.post("/variants/{variant_id}/prices", response_model=PriceOut, status_code=201)
def create_price(
    variant_id: UUID,
    payload: PriceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PRICE_UPDATE)),
):
    variant = db.get(ProductVariant, variant_id)
    if variant is None:
        raise NotFoundError("Varian tidak ditemukan.")
    if payload.unit_price < 0:
        raise BusinessRuleError("Harga tidak boleh negatif.", code="INVALID_PRICE")
    _validate_price_range(db, variant_id, payload.unit_id, payload.min_qty, payload.max_qty)
    price = ProductPrice(variant_id=variant_id, **payload.model_dump())
    db.add(price)
    _record_price_history(db, variant_id, payload.unit_id, None, payload.unit_price, user.id)
    audit.log_action(
        db, action="price.create", entity_type="variant", entity_id=variant_id, actor_id=user.id
    )
    db.commit()
    db.refresh(price)
    return price


@router.patch("/prices/{price_id}", response_model=PriceOut)
def update_price(
    price_id: UUID,
    payload: PriceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PRICE_UPDATE)),
):
    price = db.get(ProductPrice, price_id)
    if price is None:
        raise NotFoundError("Harga tidak ditemukan.")
    updates = payload.model_dump(exclude_unset=True)
    min_qty = updates.get("min_qty", price.min_qty)
    max_qty = payload.max_qty if "max_qty" in payload.model_fields_set else price.max_qty
    if (
        "unit_price" in payload.model_fields_set
        or "min_qty" in payload.model_fields_set
        or "max_qty" in payload.model_fields_set
    ):
        _validate_price_range(
            db, price.variant_id, price.unit_id, min_qty, max_qty, exclude_id=price.id
        )
    old_price = Decimal(price.unit_price)
    for key, value in updates.items():
        setattr(price, key, value)
    if "unit_price" in updates and Decimal(updates["unit_price"]) != old_price:
        _record_price_history(
            db, price.variant_id, price.unit_id, old_price, Decimal(updates["unit_price"]), user.id
        )
    audit.log_action(
        db, action="price.update", entity_type="price", entity_id=price.id, actor_id=user.id
    )
    db.commit()
    db.refresh(price)
    return price


@router.post("/prices/{price_id}/deactivate", response_model=PriceOut)
def deactivate_price(
    price_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PRICE_UPDATE)),
):
    price = db.get(ProductPrice, price_id)
    if price is None:
        raise NotFoundError("Harga tidak ditemukan.")
    price.is_active = False
    audit.log_action(
        db, action="price.deactivate", entity_type="price", entity_id=price.id, actor_id=user.id
    )
    db.commit()
    db.refresh(price)
    return price


@router.get("/variants/{variant_id}/price-history")
def price_history(
    variant_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PRICE_READ)),
):
    rows = (
        db.execute(
            select(PriceHistory)
            .where(PriceHistory.variant_id == variant_id)
            .order_by(PriceHistory.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": str(r.id),
            "unit_id": str(r.unit_id),
            "old_price": str(r.old_price) if r.old_price is not None else None,
            "new_price": str(r.new_price),
            "changed_by": str(r.changed_by),
            "created_at": r.created_at,
        }
        for r in rows
    ]
