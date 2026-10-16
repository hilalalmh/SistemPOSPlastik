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


def _make_sale(client, headers, setup, session_id, *, qty="5", amount="100000"):
    response = client.post(
        "/api/v1/sales",
        json={
            "cash_session_id": session_id,
            "items": [
                {
                    "variant_id": setup["variant_id"],
                    "unit_id": setup["unit_pcs"],
                    "quantity": qty,
                }
            ],
            "payments": [{"method": "cash", "amount": amount}],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_returnable_items_endpoint(client, auth_headers, cash_session, make_variant):
    setup = make_variant(stock=Decimal(1000))
    sale = _make_sale(client, auth_headers, setup, cash_session)

    response = client.get(f"/api/v1/sales/{sale['id']}/returnable-items", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["number"] == sale["number"]
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == "5.0000"
    assert body["items"][0]["remaining_quantity"] == "5.0000"


def test_confirm_resellable_restores_stock(client, auth_headers, cash_session, make_variant):
    setup = make_variant(stock=Decimal(1000))
    sale = _make_sale(client, auth_headers, setup, cash_session)
    assert _qty(setup["variant_id"]) == Decimal(995)

    item_id = client.get(
        f"/api/v1/sales/{sale['id']}/returnable-items", headers=auth_headers
    ).json()["items"][0]["id"]

    created = client.post(
        "/api/v1/returns",
        json={
            "sale_id": sale["id"],
            "reason": "Salah beli",
            "refund_method": "cash",
            "items": [{"sale_item_id": item_id, "quantity": "2", "condition": "resellable"}],
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "draft"
    assert body["refund_amount"] == "1600.00"
    assert body["number"].startswith("RTR-")
    assert _qty(setup["variant_id"]) == Decimal(995)

    confirmed = client.post(f"/api/v1/returns/{body['id']}/confirm", headers=auth_headers)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "confirmed"
    assert _qty(setup["variant_id"]) == Decimal(997)


def test_damaged_condition_does_not_restore_stock(client, auth_headers, cash_session, make_variant):
    setup = make_variant(stock=Decimal(1000))
    sale = _make_sale(client, auth_headers, setup, cash_session)
    item_id = client.get(
        f"/api/v1/sales/{sale['id']}/returnable-items", headers=auth_headers
    ).json()["items"][0]["id"]

    created = client.post(
        "/api/v1/returns",
        json={
            "sale_id": sale["id"],
            "reason": "Barang rusak",
            "items": [{"sale_item_id": item_id, "quantity": "3", "condition": "damaged"}],
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    client.post(f"/api/v1/returns/{created.json()['id']}/confirm", headers=auth_headers)
    assert _qty(setup["variant_id"]) == Decimal(995)


def test_return_quantity_exceeds_remaining(client, auth_headers, cash_session, make_variant):
    setup = make_variant(stock=Decimal(1000))
    sale = _make_sale(client, auth_headers, setup, cash_session)
    item_id = client.get(
        f"/api/v1/sales/{sale['id']}/returnable-items", headers=auth_headers
    ).json()["items"][0]["id"]

    response = client.post(
        "/api/v1/returns",
        json={
            "sale_id": sale["id"],
            "reason": "Terlalu banyak",
            "items": [{"sale_item_id": item_id, "quantity": "6", "condition": "resellable"}],
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "QUANTITY_EXCEEDS_RETURNABLE"


def test_cumulative_returns_cannot_exceed_sale(client, auth_headers, cash_session, make_variant):
    setup = make_variant(stock=Decimal(1000))
    sale = _make_sale(client, auth_headers, setup, cash_session)
    item_id = client.get(
        f"/api/v1/sales/{sale['id']}/returnable-items", headers=auth_headers
    ).json()["items"][0]["id"]

    first = client.post(
        "/api/v1/returns",
        json={
            "sale_id": sale["id"],
            "reason": "Sebagian",
            "items": [{"sale_item_id": item_id, "quantity": "3", "condition": "resellable"}],
        },
        headers=auth_headers,
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/returns",
        json={
            "sale_id": sale["id"],
            "reason": "Sisanya kebanyakan",
            "items": [{"sale_item_id": item_id, "quantity": "3", "condition": "resellable"}],
        },
        headers=auth_headers,
    )
    assert second.status_code == 422
    assert second.json()["error"]["code"] == "QUANTITY_EXCEEDS_RETURNABLE"


def test_cancel_return_frees_quantity(client, auth_headers, cash_session, make_variant):
    setup = make_variant(stock=Decimal(1000))
    sale = _make_sale(client, auth_headers, setup, cash_session)
    item_id = client.get(
        f"/api/v1/sales/{sale['id']}/returnable-items", headers=auth_headers
    ).json()["items"][0]["id"]

    created = client.post(
        "/api/v1/returns",
        json={
            "sale_id": sale["id"],
            "reason": "Batal",
            "items": [{"sale_item_id": item_id, "quantity": "5", "condition": "resellable"}],
        },
        headers=auth_headers,
    ).json()

    cancelled = client.post(f"/api/v1/returns/{created['id']}/cancel", headers=auth_headers)
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"

    again = client.post(
        "/api/v1/returns",
        json={
            "sale_id": sale["id"],
            "reason": "Retur ulang",
            "items": [{"sale_item_id": item_id, "quantity": "5", "condition": "resellable"}],
        },
        headers=auth_headers,
    )
    assert again.status_code == 201, again.text
    assert again.json()["status"] == "draft"
    assert again.json()["refund_amount"] == "4000.00"
    assert again.json()["number"].startswith("RTR-")
    assert again.json()["items"][0]["sku"] is not None
    assert again.json()["items"][0]["product_name"] is not None
