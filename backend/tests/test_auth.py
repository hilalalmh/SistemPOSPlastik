def test_login_and_me(client, owner_username):
    response = client.post(
        "/api/v1/auth/login", json={"username": owner_username, "password": "secret123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert "sale.create" in body["user"]["permissions"]

    headers = {"Authorization": f"Bearer {body['access_token']}"}
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "owner"


def test_login_wrong_password(client, owner_username):
    response = client.post(
        "/api/v1/auth/login", json={"username": owner_username, "password": "wrong"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_me_requires_auth(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_permission_denied(client, cashier_headers):
    response = client.get("/api/v1/audit-logs", headers=cashier_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
