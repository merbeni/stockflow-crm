"""Integration tests for /invoices routes — Gemini is always mocked."""
import json
import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

_FAKE_GEMINI_RESPONSE = {
    "supplier": "Acme Corp",
    "date": "2024-01-15",
    "items": [
        {
            "description": "Blue Widget",
            "quantity": 10,
            "unit_price": 5.00,
            "confidence": "high",
        },
        {
            "description": "Red Gadget",
            "quantity": 5,
            "unit_price": 12.50,
            "confidence": "medium",
        },
    ],
}


def _upload_invoice(client, auth_headers, mocker, gemini_data=None):
    """Upload a fake invoice file with a mocked Gemini response."""
    gemini_data = gemini_data or _FAKE_GEMINI_RESPONSE
    mocker.patch(
        "app.services.invoice.invoice_service.process_invoice_file",
        return_value=gemini_data,
    )
    fake_file = b"%PDF-1.4 fake pdf content"
    resp = client.post(
        "/invoices/process",
        files={"file": ("invoice.pdf", fake_file, "application/pdf")},
        headers=auth_headers,
    )
    return resp


# ── process ───────────────────────────────────────────────────────────────────

class TestProcessInvoice:
    def test_process_invoice_success(self, client, auth_headers, mocker):
        resp = _upload_invoice(client, auth_headers, mocker)
        assert resp.status_code == 201
        data = resp.json()
        assert "invoice_id" in data
        assert len(data["items"]) == 2
        assert data["supplier"] == "Acme Corp"
        assert data["date"] == "2024-01-15"

    def test_process_invoice_with_matching_supplier(self, client, auth_headers, mocker, make_supplier):
        make_supplier(name="Acme Corp", email="acme@test.com")
        resp = _upload_invoice(client, auth_headers, mocker)
        assert resp.status_code == 201
        assert resp.json()["supplier_id"] is not None

    def test_process_invoice_suggests_existing_product(self, client, auth_headers, mocker, make_product):
        make_product(sku="BW-001", name="Blue Widget")
        resp = _upload_invoice(client, auth_headers, mocker)
        assert resp.status_code == 201
        items = resp.json()["items"]
        blue_item = next(i for i in items if "Blue Widget" in i["description"])
        assert blue_item["suggested_product_id"] is not None
        assert blue_item["suggested_product_name"] == "Blue Widget"

    def test_process_invoice_no_suggestions_for_unknown_items(self, client, auth_headers, mocker):
        resp = _upload_invoice(client, auth_headers, mocker)
        assert resp.status_code == 201
        for item in resp.json()["items"]:
            assert item["suggested_product_id"] is None

    def test_process_invoice_requires_auth(self, client, mocker):
        mocker.patch(
            "app.services.invoice.invoice_service.process_invoice_file",
            return_value=_FAKE_GEMINI_RESPONSE,
        )
        resp = client.post(
            "/invoices/process",
            files={"file": ("invoice.pdf", b"data", "application/pdf")},
        )
        assert resp.status_code == 401

    def test_process_invoice_invalid_mime_type_returns_415(self, client, auth_headers):
        resp = client.post(
            "/invoices/process",
            files={"file": ("doc.txt", b"hello", "text/plain")},
            headers=auth_headers,
        )
        assert resp.status_code == 415

    def test_process_invoice_gemini_json_error_returns_422(self, client, auth_headers, mocker):
        # The router maps ValueError (bad Gemini JSON) → 422 Unprocessable Entity
        mocker.patch(
            "app.services.invoice.invoice_service.process_invoice_file",
            side_effect=ValueError("Gemini returned non-JSON content: ..."),
        )
        resp = client.post(
            "/invoices/process",
            files={"file": ("invoice.pdf", b"data", "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 422


# ── confirm ───────────────────────────────────────────────────────────────────

class TestConfirmInvoice:
    def test_confirm_invoice_with_existing_product(self, client, auth_headers, mocker, make_product):
        product = make_product(sku="BW-001", name="Blue Widget", current_stock="0.000")
        process_resp = _upload_invoice(client, auth_headers, mocker)
        invoice_id = process_resp.json()["invoice_id"]
        items = process_resp.json()["items"]

        confirm_payload = {
            "items": [
                {"invoice_item_id": items[0]["id"], "product_id": product["id"]},
                {"invoice_item_id": items[1]["id"], "skip": True},
            ]
        }
        resp = client.post(f"/invoices/{invoice_id}/confirm", json=confirm_payload, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

    def test_confirm_invoice_updates_product_stock(self, client, auth_headers, mocker, make_product, db):
        from app.models.product import Product
        product = make_product(sku="BW-002", name="Blue Widget", current_stock="20.000")
        process_resp = _upload_invoice(client, auth_headers, mocker)
        invoice_id = process_resp.json()["invoice_id"]
        items = process_resp.json()["items"]

        client.post(f"/invoices/{invoice_id}/confirm", json={
            "items": [
                {"invoice_item_id": items[0]["id"], "product_id": product["id"]},
                {"invoice_item_id": items[1]["id"], "skip": True},
            ]
        }, headers=auth_headers)

        db.refresh(db.get(Product, product["id"]))
        updated = db.get(Product, product["id"])
        # Original 20 + 10 from invoice item
        assert float(updated.current_stock) == 30.0

    def test_confirm_invoice_creates_new_product(self, client, auth_headers, mocker):
        process_resp = _upload_invoice(client, auth_headers, mocker)
        invoice_id = process_resp.json()["invoice_id"]
        items = process_resp.json()["items"]

        resp = client.post(f"/invoices/{invoice_id}/confirm", json={
            "items": [
                {
                    "invoice_item_id": items[0]["id"],
                    "new_product": {
                        "sku": "NEW-BW-001",
                        "name": "New Blue Widget",
                        "price": "5.00",
                        "minimum_stock": "0.000",
                    },
                },
                {"invoice_item_id": items[1]["id"], "skip": True},
            ]
        }, headers=auth_headers)
        assert resp.status_code == 200

        # New product should exist in inventory
        products_resp = client.get("/products", headers=auth_headers)
        skus = [p["sku"] for p in products_resp.json()]
        assert "NEW-BW-001" in skus

    def test_confirm_invoice_creates_supplier_sku_mapping(self, client, auth_headers, mocker, make_product, make_supplier, db):
        from app.models.product_supplier_mapping import ProductSupplierMapping
        supplier = make_supplier(name="Acme Corp", email="acme@test.com")
        product = make_product(sku="MAP-001", name="Blue Widget", current_stock="0.000")
        process_resp = _upload_invoice(client, auth_headers, mocker)
        invoice_id = process_resp.json()["invoice_id"]
        items = process_resp.json()["items"]

        client.post(f"/invoices/{invoice_id}/confirm", json={
            "supplier_id": supplier["id"],
            "items": [
                {
                    "invoice_item_id": items[0]["id"],
                    "product_id": product["id"],
                    "supplier_sku": "ACME-BW-XYZ",
                },
                {"invoice_item_id": items[1]["id"], "skip": True},
            ]
        }, headers=auth_headers)

        mapping = db.query(ProductSupplierMapping).filter(
            ProductSupplierMapping.supplier_id == supplier["id"],
            ProductSupplierMapping.supplier_sku == "ACME-BW-XYZ",
        ).first()
        assert mapping is not None
        assert mapping.product_id == product["id"]

    def test_confirm_already_confirmed_invoice_returns_400(self, client, auth_headers, mocker, make_product):
        product = make_product(sku="CONF-001", name="Blue Widget", current_stock="0.000")
        process_resp = _upload_invoice(client, auth_headers, mocker)
        invoice_id = process_resp.json()["invoice_id"]
        items = process_resp.json()["items"]

        confirm_payload = {
            "items": [
                {"invoice_item_id": items[0]["id"], "product_id": product["id"]},
                {"invoice_item_id": items[1]["id"], "skip": True},
            ]
        }
        client.post(f"/invoices/{invoice_id}/confirm", json=confirm_payload, headers=auth_headers)
        resp = client.post(f"/invoices/{invoice_id}/confirm", json=confirm_payload, headers=auth_headers)
        assert resp.status_code == 400


# ── reject ────────────────────────────────────────────────────────────────────

class TestRejectInvoice:
    def test_reject_pending_invoice(self, client, auth_headers, mocker):
        process_resp = _upload_invoice(client, auth_headers, mocker)
        invoice_id = process_resp.json()["invoice_id"]

        resp = client.post(f"/invoices/{invoice_id}/reject", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_reject_already_rejected_invoice_returns_400(self, client, auth_headers, mocker):
        process_resp = _upload_invoice(client, auth_headers, mocker)
        invoice_id = process_resp.json()["invoice_id"]
        client.post(f"/invoices/{invoice_id}/reject", headers=auth_headers)
        resp = client.post(f"/invoices/{invoice_id}/reject", headers=auth_headers)
        assert resp.status_code == 400

    def test_reject_nonexistent_invoice_returns_400(self, client, auth_headers):
        # The router catches ValueError from the service and returns 400
        resp = client.post("/invoices/9999/reject", headers=auth_headers)
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"].lower()


# ── list / get ────────────────────────────────────────────────────────────────

class TestListGetInvoice:
    def test_list_invoices_empty(self, client, auth_headers):
        resp = client.get("/invoices", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_invoices_returns_processed(self, client, auth_headers, mocker):
        _upload_invoice(client, auth_headers, mocker)
        resp = client.get("/invoices", headers=auth_headers)
        assert len(resp.json()) == 1

    def test_get_invoice_success(self, client, auth_headers, mocker):
        process_resp = _upload_invoice(client, auth_headers, mocker)
        invoice_id = process_resp.json()["invoice_id"]
        resp = client.get(f"/invoices/{invoice_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == invoice_id
        assert len(resp.json()["items"]) == 2

    def test_get_nonexistent_invoice_returns_404(self, client, auth_headers):
        resp = client.get("/invoices/9999", headers=auth_headers)
        assert resp.status_code == 404
