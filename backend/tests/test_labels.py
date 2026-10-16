import uuid

from app.core.database import SessionLocal
from app.models.product import ProductVariant


def test_label_preview_returns_code128_svg(client, auth_headers, make_variant):
    variant = make_variant()
    db = SessionLocal()
    try:
        barcode = db.get(ProductVariant, uuid.UUID(variant["variant_id"])).barcode
    finally:
        db.close()

    response = client.post(
        "/api/v1/labels/preview",
        json={"items": [{"variant_id": variant["variant_id"], "copies": 3}]},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 1
    label = data["labels"][0]
    assert label["code"] == barcode
    assert label["has_barcode"] is True
    assert label["copies"] == 3
    assert label["barcode_svg"].startswith("data:image/svg+xml;base64,")


def test_label_preview_empty_items_rejected(client, auth_headers):
    response = client.post("/api/v1/labels/preview", json={"items": []}, headers=auth_headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NO_ITEMS"


def test_label_preview_unknown_variant(client, auth_headers):
    response = client.post(
        "/api/v1/labels/preview",
        json={"items": [{"variant_id": str(uuid.uuid4()), "copies": 1}]},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_list_variants_includes_product_name(client, auth_headers, make_variant):
    variant = make_variant()
    response = client.get(
        f"/api/v1/variants?q={variant['sku']}",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    rows = response.json()["data"]
    assert rows[0]["product_name"]
