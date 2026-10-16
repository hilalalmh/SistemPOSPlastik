from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import StockBalance


def _qty(variant_id):
    db = SessionLocal()
    try:
        balance = db.execute(
            select(StockBalance).where(StockBalance.variant_id == UUID(variant_id))
        ).scalar_one()
        return Decimal(balance.quantity)
    finally:
        db.close()


def _payload(setup, session_id, *, qty="5", unit=None, amount="100000", method="cash"):
    return {
        "cash_session_id": session_id,
        "items": [
            {
                "variant_id": setup["variant_id"],
                "unit_id": unit or setup["unit_pcs"],
                "quantity": qty,
            }
        ],
        "payments": [{"method": method, "amount": amount}],
    }


def test_quote(client, auth_headers, make_variant):
    setup = make_variant()
    response = client.post(
        "/api/v1/sales/quotes",
        json={
            "items": [
                {"variant_id": setup["variant_id"], "unit_id": setup["unit_pcs"], "quantity": "10"}
            ]
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["subtotal"] == "8000.00"
    assert body["total"] == "8000.00"
    assert body["items"][0]["stock_sufficient"] is True


def test_checkout_cash_success(client, auth_headers, make_variant, cash_session):
    setup = make_variant(stock=Decimal(1000))
    before = _qty(setup["variant_id"])

    response = client.post(
        "/api/v1/sales", json=_payload(setup, cash_session), headers=auth_headers
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["total"] == "4000.00"
    assert body["change_total"] == "96000.00"
    assert body["number"].startswith("SLS-")
    assert len(body["items"]) == 1

    after = _qty(setup["variant_id"])
    assert after == before - Decimal(5)


def test_checkout_pak_conversion(client, auth_headers, make_variant, cash_session):
    setup = make_variant(stock=Decimal(1000))
    response = client.post(
        "/api/v1/sales",
        json=_payload(setup, cash_session, qty="2", unit=setup["unit_pak"], amount="20000"),
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["total"] == "14000.00"
    assert _qty(setup["variant_id"]) == Decimal(1000) - Decimal(20)


def test_checkout_insufficient_stock(client, auth_headers, make_variant, cash_session):
    setup = make_variant(stock=Decimal(3))
    response = client.post(
        "/api/v1/sales", json=_payload(setup, cash_session, qty="10"), headers=auth_headers
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INSUFFICIENT_STOCK"


def test_checkout_requires_open_session(client, cashier_headers, make_variant):
    setup = make_variant(stock=Decimal(100))
    import uuid

    response = client.post(
        "/api/v1/sales",
        json=_payload(setup, str(uuid.uuid4())),
        headers=cashier_headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SESSION_REQUIRED"


def test_checkout_idempotency(client, auth_headers, make_variant, cash_session):
    setup = make_variant(stock=Decimal(1000))
    key = "idem-test-key-001"
    headers = {**auth_headers, "Idempotency-Key": key}
    payload = _payload(setup, cash_session)

    first = client.post("/api/v1/sales", json=payload, headers=headers)
    second = client.post("/api/v1/sales", json=payload, headers=headers)

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["number"] == second.json()["number"]
    assert _qty(setup["variant_id"]) == Decimal(1000) - Decimal(5)


def test_void_restores_stock(client, auth_headers, make_variant, cash_session):
    setup = make_variant(stock=Decimal(1000))
    sale = client.post(
        "/api/v1/sales", json=_payload(setup, cash_session), headers=auth_headers
    ).json()
    assert _qty(setup["variant_id"]) == Decimal(995)

    response = client.post(
        f"/api/v1/sales/{sale['id']}/void",
        json={"reason": "Salah input"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "voided"
    assert _qty(setup["variant_id"]) == Decimal(1000)


def test_list_sales_date_filter_includes_today(client, auth_headers, make_variant, cash_session):
    from datetime import date

    setup = make_variant(stock=Decimal(1000))
    sale = client.post(
        "/api/v1/sales", json=_payload(setup, cash_session), headers=auth_headers
    ).json()

    today = date.today().isoformat()
    response = client.get(f"/api/v1/sales?from={today}&to={today}", headers=auth_headers)
    assert response.status_code == 200, response.text
    numbers = [s["number"] for s in response.json()["data"]]
    assert sale["number"] in numbers


def test_cash_drawer_excludes_change(client, auth_headers, make_variant, cash_session):
    setup = make_variant(stock=Decimal(1000))
    sale = client.post(
        "/api/v1/sales", json=_payload(setup, cash_session), headers=auth_headers
    ).json()
    assert sale["total"] == "4000.00"
    assert sale["change_total"] == "96000.00"

    detail = client.get(f"/api/v1/cash-sessions/{cash_session}", headers=auth_headers).json()
    sale_movements = [m for m in detail["movements"] if m["type"] == "sale_cash"]
    assert len(sale_movements) == 1
    assert Decimal(sale_movements[0]["amount"]) == Decimal("4000.00")

    client.post(
        f"/api/v1/sales/{sale['id']}/void",
        json={"reason": "Kembalian salah"},
        headers=auth_headers,
    )
    detail = client.get(f"/api/v1/cash-sessions/{cash_session}", headers=auth_headers).json()
    refunds = [m for m in detail["movements"] if m["type"] == "refund"]
    assert len(refunds) == 1
    assert Decimal(refunds[0]["amount"]) == Decimal("-4000.00")
