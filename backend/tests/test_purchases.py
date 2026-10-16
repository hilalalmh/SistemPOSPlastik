import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.inventory import StockBalance


@pytest.fixture()
def supplier_id(client, auth_headers):
    response = client.post(
        "/api/v1/suppliers", json={"name": f"Supplier {uuid.uuid4().hex[:6]}"}, headers=auth_headers
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_purchase(
    client,
    headers,
    supplier_id,
    variant,
    *,
    qty="5",
    cost="6000",
    unit_key="unit_pak",
    discount="0",
    additional="0",
    order=False,
):
    body = {
        "supplier_id": supplier_id,
        "invoice_no": "INV-1",
        "additional_cost": additional,
        "discount_amount": discount,
        "order": order,
        "items": [
            {
                "variant_id": variant["variant_id"],
                "unit_id": variant[unit_key],
                "quantity": qty,
                "unit_cost": cost,
                "discount_amount": "0",
            }
        ],
    }
    response = client.post("/api/v1/purchases", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _balance(variant_id):
    db = SessionLocal()
    try:
        row = db.execute(
            select(StockBalance).where(StockBalance.variant_id == uuid.UUID(variant_id))
        ).scalar_one_or_none()
        return (Decimal(row.quantity), Decimal(row.avg_cost)) if row else (Decimal(0), Decimal(0))
    finally:
        db.close()


def test_create_purchase_computes_totals(client, auth_headers, supplier_id, make_variant):
    variant = make_variant(stock=Decimal(0))
    purchase = _create_purchase(
        client, auth_headers, supplier_id, variant, qty="5", cost="6000", additional="10000"
    )
    assert purchase["status"] == "draft"
    assert Decimal(purchase["subtotal"]) == Decimal("30000.00")
    assert Decimal(purchase["discount_total"]) == Decimal("0.00")
    assert Decimal(purchase["total"]) == Decimal("40000.00")
    item = purchase["items"][0]
    assert Decimal(item["remaining_quantity"]) == Decimal("5.0000")
    assert Decimal(item["base_unit_cost"]) == Decimal("800.0000")


def test_receive_increases_stock_and_average_cost(client, auth_headers, supplier_id, make_variant):
    variant = make_variant(stock=Decimal(0))
    purchase = _create_purchase(
        client, auth_headers, supplier_id, variant, qty="5", cost="6000", additional="10000"
    )
    item_id = purchase["items"][0]["id"]

    response = client.post(
        f"/api/v1/purchases/{purchase['id']}/receive",
        json={"items": [{"purchase_item_id": item_id, "quantity": "5"}]},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "received"
    assert len(data["receipts"]) == 1
    assert data["receipts"][0]["number"].startswith("RCV")

    qty, avg = _balance(variant["variant_id"])
    assert qty == Decimal("50.0000")
    assert avg == Decimal("800.0000")


def test_partial_receive_flow(client, auth_headers, supplier_id, make_variant):
    variant = make_variant(stock=Decimal(0))
    purchase = _create_purchase(client, auth_headers, supplier_id, variant, qty="5", cost="6000")

    item_id = purchase["items"][0]["id"]
    partial = client.post(
        f"/api/v1/purchases/{purchase['id']}/receive",
        json={"items": [{"purchase_item_id": item_id, "quantity": "2"}]},
        headers=auth_headers,
    )
    assert partial.status_code == 200, partial.text
    assert partial.json()["status"] == "partially_received"
    assert Decimal(partial.json()["items"][0]["remaining_quantity"]) == Decimal("3.0000")

    qty, _ = _balance(variant["variant_id"])
    assert qty == Decimal("20.0000")

    final = client.post(
        f"/api/v1/purchases/{purchase['id']}/receive",
        json={"items": [{"purchase_item_id": item_id, "quantity": "3"}]},
        headers=auth_headers,
    )
    assert final.status_code == 200, final.text
    assert final.json()["status"] == "received"

    qty, _ = _balance(variant["variant_id"])
    assert qty == Decimal("50.0000")


def test_over_receive_rejected(client, auth_headers, supplier_id, make_variant):
    variant = make_variant(stock=Decimal(0))
    purchase = _create_purchase(client, auth_headers, supplier_id, variant, qty="5", cost="6000")
    item_id = purchase["items"][0]["id"]

    response = client.post(
        f"/api/v1/purchases/{purchase['id']}/receive",
        json={"items": [{"purchase_item_id": item_id, "quantity": "6"}]},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "OVER_RECEIVE"


def test_cancel_blocks_receive(client, auth_headers, supplier_id, make_variant):
    variant = make_variant(stock=Decimal(0))
    purchase = _create_purchase(client, auth_headers, supplier_id, variant)

    cancelled = client.post(f"/api/v1/purchases/{purchase['id']}/cancel", headers=auth_headers)
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"

    item_id = purchase["items"][0]["id"]
    response = client.post(
        f"/api/v1/purchases/{purchase['id']}/receive",
        json={"items": [{"purchase_item_id": item_id, "quantity": "1"}]},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert _balance(variant["variant_id"])[0] == Decimal("0.0000")


def test_cashier_cannot_create_purchase(client, cashier_headers, supplier_id, make_variant):
    variant = make_variant(stock=Decimal(0))
    response = client.post(
        "/api/v1/purchases",
        json={
            "supplier_id": supplier_id,
            "items": [
                {
                    "variant_id": variant["variant_id"],
                    "unit_id": variant["unit_pcs"],
                    "quantity": "1",
                    "unit_cost": "500",
                }
            ],
        },
        headers=cashier_headers,
    )
    assert response.status_code == 403
