from datetime import date


def _today() -> str:
    return date.today().isoformat()


def test_create_and_list_category(client, auth_headers):
    name = f"Kategori {date.today().isoformat()}"
    response = client.post(
        "/api/v1/expense-categories",
        json={"name": name},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    category = response.json()
    assert category["name"] == name

    listing = client.get("/api/v1/expense-categories", headers=auth_headers)
    assert listing.status_code == 200, listing.text
    assert any(c["id"] == category["id"] for c in listing.json()["data"])


def test_duplicate_category_conflict(client, auth_headers):
    response = client.post(
        "/api/v1/expense-categories",
        json={"name": "Kategori Duplikat"},
        headers=auth_headers,
    )
    assert response.status_code in (201, 409)
    again = client.post(
        "/api/v1/expense-categories",
        json={"name": "Kategori Duplikat"},
        headers=auth_headers,
    )
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "CATEGORY_EXISTS"


def test_create_expense_and_list(client, auth_headers):
    category = client.post(
        "/api/v1/expense-categories",
        json={"name": f"Sewa {date.today().isoformat()}"},
        headers=auth_headers,
    ).json()

    response = client.post(
        "/api/v1/expenses",
        json={
            "category_id": category["id"],
            "expense_date": _today(),
            "amount": "150000",
            "payment_method": "cash",
            "description": "Sewa kios",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["amount"] == "150000.00"
    assert body["category_name"] == category["name"]

    listing = client.get("/api/v1/expenses", headers=auth_headers)
    assert listing.status_code == 200, listing.text
    assert any(e["id"] == body["id"] for e in listing.json()["data"])


def test_create_expense_invalid_amount(client, auth_headers):
    response = client.post(
        "/api/v1/expenses",
        json={
            "expense_date": _today(),
            "amount": "0",
            "payment_method": "cash",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_AMOUNT"


def test_cancel_expense(client, auth_headers):
    created = client.post(
        "/api/v1/expenses",
        json={
            "expense_date": _today(),
            "amount": "20000",
            "payment_method": "transfer",
        },
        headers=auth_headers,
    ).json()

    cancelled = client.post(f"/api/v1/expenses/{created['id']}/cancel", headers=auth_headers)
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["cancelled_at"] is not None

    again = client.post(f"/api/v1/expenses/{created['id']}/cancel", headers=auth_headers)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "EXPENSE_ALREADY_CANCELLED"


def test_expense_report(client, auth_headers):
    category = client.post(
        "/api/v1/expense-categories",
        json={"name": f"Laporan {date.today().isoformat()}"},
        headers=auth_headers,
    ).json()
    client.post(
        "/api/v1/expenses",
        json={
            "category_id": category["id"],
            "expense_date": _today(),
            "amount": "75000",
            "payment_method": "cash",
        },
        headers=auth_headers,
    )

    response = client.get(
        f"/api/v1/reports/expenses?from={_today()}&to={_today()}",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["from_date"] == _today()
    assert body["count"] >= 1
    assert any(row["category_id"] == category["id"] for row in body["by_category"])
