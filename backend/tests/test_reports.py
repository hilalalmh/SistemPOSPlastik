from datetime import date
from decimal import Decimal


def _today() -> str:
    return date.today().isoformat()


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


def test_dashboard_payment_breakdown_sums_to_net(client, auth_headers, cash_session, make_variant):
    setup = make_variant(stock=Decimal(1000))
    _make_sale(client, auth_headers, setup, cash_session)

    response = client.get(f"/api/v1/reports/dashboard?target={_today()}", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    breakdown = sum((Decimal(row["amount"]) for row in body["payment_breakdown"]), Decimal(0))
    assert breakdown == Decimal(body["net_revenue"])


def test_sales_payments_report(client, auth_headers, cash_session, make_variant):
    setup = make_variant(stock=Decimal(1000))
    _make_sale(client, auth_headers, setup, cash_session)

    dashboard = client.get(
        f"/api/v1/reports/dashboard?target={_today()}", headers=auth_headers
    ).json()
    response = client.get(
        f"/api/v1/reports/sales/payments?from={_today()}&to={_today()}",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert any(row["method"] == "cash" for row in body["data"])
    assert Decimal(body["total"]) == Decimal(dashboard["net_revenue"])


def test_cashiers_report(client, auth_headers, cash_session, make_variant):
    setup = make_variant(stock=Decimal(1000))
    _make_sale(client, auth_headers, setup, cash_session)

    response = client.get(
        f"/api/v1/reports/cashiers?from={_today()}&to={_today()}",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["data"]) >= 1
    assert body["data"][0]["sales_count"] >= 1
    assert "gross_profit" in body["data"][0]


def test_top_products_by_quantity_and_value(client, auth_headers, cash_session, make_variant):
    setup = make_variant(stock=Decimal(1000))
    _make_sale(client, auth_headers, setup, cash_session)

    by_qty = client.get(
        f"/api/v1/reports/products/top?from={_today()}&to={_today()}&by=quantity",
        headers=auth_headers,
    )
    assert by_qty.status_code == 200, by_qty.text
    data = by_qty.json()["data"]
    assert any(row["variant_id"] == setup["variant_id"] for row in data)

    by_value = client.get(
        f"/api/v1/reports/top-products?from={_today()}&to={_today()}&by=value",
        headers=auth_headers,
    )
    assert by_value.status_code == 200, by_value.text


def test_purchases_report(client, auth_headers):
    response = client.get(
        f"/api/v1/reports/purchases?from={_today()}&to={_today()}",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["from_date"] == _today()
    assert isinstance(body["data"], list)
