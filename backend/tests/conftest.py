import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://postgres:postgres@localhost:5432/pos_test_db"
os.environ["SECRET_KEY"] = "test-secret-key"

import uuid  # noqa: E402
from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    CashSession,
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
from app.permissions import ALL_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for code, description in ALL_PERMISSIONS.items():
            db.add(Permission(code=code, description=description))
        db.flush()
        perm_map = {p.code: p for p in db.execute(select(Permission)).scalars()}
        for name, codes in DEFAULT_ROLE_PERMISSIONS.items():
            role = Role(name=name, is_system=True)
            db.add(role)
            db.flush()
            for code in codes:
                db.add(RolePermission(role_id=role.id, permission_id=perm_map[code].id))
        db.add(StoreSetting(store_name="Test Store", discount_max_percent_cashier=Decimal("10.00")))
        db.add(Location(name="Main", code="MAIN", is_default=True))
        db.add(Category(name="Umum"))
        db.commit()
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def _create_user(username, role_name, password="secret123"):
    db = SessionLocal()
    try:
        role = db.execute(select(Role).where(Role.name == role_name)).scalar_one()
        user = User(
            name=username.title(),
            username=username,
            password_hash=hash_password(password),
            role_id=role.id,
        )
        db.add(user)
        db.commit()
        return str(user.id)
    finally:
        db.close()


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def _login(client, username, password="secret123"):
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def owner_username():
    name = f"owner_{uuid.uuid4().hex[:6]}"
    _create_user(name, "owner")
    return name


@pytest.fixture()
def cashier_username():
    name = f"cashier_{uuid.uuid4().hex[:6]}"
    _create_user(name, "cashier")
    return name


@pytest.fixture()
def auth_headers(client, owner_username):
    return _login(client, owner_username)


@pytest.fixture()
def cashier_headers(client, cashier_username):
    return _login(client, cashier_username)


@pytest.fixture()
def make_variant():
    """Create a fresh sellable variant with conversion + prices and opening stock."""
    created_sessions = []

    def _factory(*, stock=Decimal(1000), cost=Decimal(500)):
        db = SessionLocal()
        try:
            location = db.execute(
                select(Location).where(Location.is_default.is_(True))
            ).scalar_one()
            unit_pcs = db.execute(select(Unit).where(Unit.name == "Pcs")).scalar_one_or_none()
            if unit_pcs is None:
                unit_pcs = Unit(name="Pcs", symbol="pcs", allows_fraction=True)
                db.add(unit_pcs)
            unit_pak = db.execute(select(Unit).where(Unit.name == "Pak")).scalar_one_or_none()
            if unit_pak is None:
                unit_pak = Unit(name="Pak", symbol="pak", allows_fraction=False)
                db.add(unit_pak)
            db.flush()

            sku = f"SKU-{uuid.uuid4().hex[:8].upper()}"
            category = db.execute(select(Category).limit(1)).scalar_one()
            product = Product(name=f"Produk {sku}", category_id=category.id)
            db.add(product)
            db.flush()
            variant = ProductVariant(
                product_id=product.id,
                sku=sku,
                barcode=uuid.uuid4().hex[:13],
                base_unit_id=unit_pcs.id,
                min_stock=Decimal(10),
            )
            db.add(variant)
            db.flush()
            db.add_all(
                [
                    ProductUnitConversion(
                        variant_id=variant.id, unit_id=unit_pcs.id, base_units_per_unit=Decimal(1)
                    ),
                    ProductUnitConversion(
                        variant_id=variant.id, unit_id=unit_pak.id, base_units_per_unit=Decimal(10)
                    ),
                    ProductPrice(
                        variant_id=variant.id,
                        unit_id=unit_pcs.id,
                        min_qty=Decimal(1),
                        unit_price=Decimal("800.00"),
                    ),
                    ProductPrice(
                        variant_id=variant.id,
                        unit_id=unit_pak.id,
                        min_qty=Decimal(1),
                        unit_price=Decimal("7000.00"),
                    ),
                ]
            )
            db.flush()
            from app.services import inventory as inventory_service

            if stock > 0:
                inventory_service.apply_movement(
                    db,
                    variant_id=variant.id,
                    location_id=location.id,
                    movement_type="opening",
                    quantity_delta=stock,
                    unit_cost=cost,
                )
            db.commit()
            result = {
                "variant_id": str(variant.id),
                "unit_pcs": str(unit_pcs.id),
                "unit_pak": str(unit_pak.id),
                "location_id": str(location.id),
                "sku": sku,
            }
            created_sessions.append(db)
            return result
        finally:
            db.close()

    yield _factory


@pytest.fixture()
def cash_session(client, auth_headers):
    response = client.post(
        "/api/v1/cash-sessions/open", json={"opening_cash": 100000}, headers=auth_headers
    )
    assert response.status_code == 201, response.text
    session_id = response.json()["id"]
    yield session_id
    db = SessionLocal()
    try:
        session = db.get(CashSession, uuid.UUID(session_id))
        if session and session.status == "open":
            session.status = "closed"
            db.commit()
    finally:
        db.close()
