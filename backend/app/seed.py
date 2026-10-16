"""Seed initial data: permissions, roles, users, store, units, sample products.

Run from the backend directory:
    python -m app.seed
"""

from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import (
    Category,
    Location,
    Permission,
    Product,
    ProductPrice,
    ProductUnitConversion,
    ProductVariant,
    Role,
    RolePermission,
    StoreSetting,
    Unit,
    User,
)
from app.permissions import ALL_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS, ROLE_DESCRIPTIONS
from app.services import inventory as inventory_service


def seed():
    db = SessionLocal()
    try:
        _seed_permissions(db)
        roles = _seed_roles(db)
        _seed_store(db)
        location = _seed_location(db)
        units = _seed_units(db)
        _seed_users(db, roles)
        _seed_products(db, units, location)
        db.commit()
        print("Seed selesai. Login admin: admin / admin123")
    finally:
        db.close()


def _seed_permissions(db) -> None:
    existing = {p.code for p in db.execute(select(Permission)).scalars()}
    for code, description in ALL_PERMISSIONS.items():
        if code not in existing:
            db.add(Permission(code=code, description=description))
    db.flush()


def _seed_roles(db) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    perm_map = {p.code: p for p in db.execute(select(Permission)).scalars()}
    for name in DEFAULT_ROLE_PERMISSIONS:
        role = db.execute(select(Role).where(Role.name == name)).scalar_one_or_none()
        if role is None:
            role = Role(name=name, description=ROLE_DESCRIPTIONS[name], is_system=True)
            db.add(role)
            db.flush()
        existing = {
            rp.permission_id
            for rp in db.execute(
                select(RolePermission).where(RolePermission.role_id == role.id)
            ).scalars()
        }
        for code in DEFAULT_ROLE_PERMISSIONS[name]:
            permission = perm_map[code]
            if permission.id not in existing:
                db.add(RolePermission(role_id=role.id, permission_id=permission.id))
        roles[name] = role
    db.flush()
    return roles


def _seed_store(db) -> None:
    if db.execute(select(StoreSetting)).scalar_one_or_none() is None:
        db.add(
            StoreSetting(
                store_name="Toko Plastik Jaya",
                address="Jl. Merdeka No. 123",
                phone="0812-0000-0000",
                receipt_header="Toko Plastik Jaya",
                receipt_footer="Terima kasih telah berbelanja",
                discount_max_percent_cashier=Decimal("10.00"),
            )
        )
        db.flush()


def _seed_location(db) -> Location:
    location = db.execute(
        select(Location).where(Location.is_default.is_(True))
    ).scalar_one_or_none()
    if location is None:
        location = Location(name="Toko Utama", code="MAIN", is_default=True)
        db.add(location)
        db.flush()
    return location


def _seed_units(db) -> dict[str, Unit]:
    definitions = [
        ("Lembar", "lbr", True),
        ("Pak", "pak", False),
        ("Bal", "bal", False),
        ("Ikat", "ikat", False),
        ("Dus", "dus", False),
        ("Buah", "buah", False),
        ("Roll", "roll", False),
        ("Meter", "m", True),
        ("Gram", "gr", True),
        ("Kilogram", "kg", True),
    ]
    units: dict[str, Unit] = {}
    for name, symbol, allows_fraction in definitions:
        unit = db.execute(select(Unit).where(Unit.name == name)).scalar_one_or_none()
        if unit is None:
            unit = Unit(name=name, symbol=symbol, allows_fraction=allows_fraction)
            db.add(unit)
            db.flush()
        units[name] = unit
    return units


def _seed_users(db, roles) -> None:
    if db.execute(select(User).where(User.username == "admin")).scalar_one_or_none() is None:
        db.add(
            User(
                name="Pemilik Toko",
                username="admin",
                password_hash=hash_password("admin123"),
                role_id=roles["owner"].id,
            )
        )
    if db.execute(select(User).where(User.username == "kasir1")).scalar_one_or_none() is None:
        db.add(
            User(
                name="Kasir Satu",
                username="kasir1",
                password_hash=hash_password("kasir123"),
                role_id=roles["cashier"].id,
            )
        )
    db.flush()


def _seed_products(db, units, location) -> None:
    if db.execute(select(Product)).first() is not None:
        return

    lembar = units["Lembar"]
    pak = units["Pak"]
    bal = units["Bal"]

    kategori = Category(name="Kantong Plastik")
    db.add(kategori)
    db.flush()

    product = Product(name="Kantong Kresek", category_id=kategori.id, brand="Plastik Jaya")
    db.add(product)
    db.flush()

    variants = [
        ("PLT-KRESEK-24x36-HITAM", "8991000000011", "24x36", "Hitam"),
        ("PLT-KRESEK-30x40-BENING", "8991000000028", "30x40", "Bening"),
    ]
    for sku, barcode, size, color in variants:
        variant = ProductVariant(
            product_id=product.id,
            sku=sku,
            barcode=barcode,
            attribute_size=size,
            attribute_color=color,
            base_unit_id=lembar.id,
            min_stock=Decimal("200"),
        )
        db.add(variant)
        db.flush()

        for unit, factor in [(lembar, Decimal(1)), (pak, Decimal(50)), (bal, Decimal(1000))]:
            db.add(
                ProductUnitConversion(
                    variant_id=variant.id, unit_id=unit.id, base_units_per_unit=factor
                )
            )

        db.add(
            ProductPrice(
                variant_id=variant.id,
                unit_id=lembar.id,
                min_qty=Decimal(1),
                unit_price=Decimal("100.00"),
            )
        )
        db.add(
            ProductPrice(
                variant_id=variant.id,
                unit_id=pak.id,
                min_qty=Decimal(1),
                max_qty=Decimal(9),
                unit_price=Decimal("5000.00"),
            )
        )
        db.add(
            ProductPrice(
                variant_id=variant.id,
                unit_id=pak.id,
                min_qty=Decimal(10),
                max_qty=Decimal(49),
                unit_price=Decimal("4700.00"),
            )
        )
        db.add(
            ProductPrice(
                variant_id=variant.id,
                unit_id=pak.id,
                min_qty=Decimal(50),
                unit_price=Decimal("4400.00"),
            )
        )
        db.add(
            ProductPrice(
                variant_id=variant.id,
                unit_id=bal.id,
                min_qty=Decimal(1),
                unit_price=Decimal("90000.00"),
            )
        )
        db.flush()

        inventory_service.apply_movement(
            db,
            variant_id=variant.id,
            location_id=location.id,
            movement_type="opening",
            quantity_delta=Decimal("2000"),
            unit_cost=Decimal("90"),
            reason="Stok awal",
        )


if __name__ == "__main__":
    seed()
