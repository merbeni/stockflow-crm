"""Integration tests for /orders routes — covers the full order lifecycle."""
import pytest


@pytest.fixture
def customer(make_customer):
    return make_customer()


@pytest.fixture
def product(make_product):
    return make_product(sku="ORD-P1", current_stock="100.000", minimum_stock="5.000")


@pytest.fixture
def pending_order(client, auth_headers, customer):
    resp = client.post("/orders", json={"customer_id": customer["id"]}, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


class TestCreateOrder:
    def test_create_order_success(self, client, auth_headers, customer):
        resp = client.post("/orders", json={"customer_id": customer["id"]}, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["customer_id"] == customer["id"]
        assert data["items"] == []
        assert float(data["total"]) == 0.0

    def test_create_order_nonexistent_customer_returns_400(self, client, auth_headers):
        # The router catches ValueError from the service and returns 400
        resp = client.post("/orders", json={"customer_id": 9999}, headers=auth_headers)
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"].lower()

    def test_create_order_requires_auth(self, client, customer):
        resp = client.post("/orders", json={"customer_id": customer["id"]})
        assert resp.status_code == 401


class TestListOrders:
    def test_list_orders_empty(self, client, auth_headers):
        resp = client.get("/orders", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_orders_returns_created(self, client, auth_headers, pending_order):
        resp = client.get("/orders", headers=auth_headers)
        assert len(resp.json()) == 1
        assert resp.json()[0]["id"] == pending_order["id"]


class TestGetOrder:
    def test_get_existing_order(self, client, auth_headers, pending_order):
        resp = client.get(f"/orders/{pending_order['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == pending_order["id"]

    def test_get_nonexistent_order_returns_404(self, client, auth_headers):
        resp = client.get("/orders/9999", headers=auth_headers)
        assert resp.status_code == 404


class TestAddItem:
    def test_add_item_to_pending_order(self, client, auth_headers, pending_order, product):
        resp = client.post(f"/orders/{pending_order['id']}/items", json={
            "product_id": product["id"],
            "quantity": "3.000",
            "unit_price": "10.00",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert float(data["total"]) == 30.0

    def test_add_item_insufficient_stock_returns_400(self, client, auth_headers, pending_order, make_product):
        low = make_product(sku="LOW-STOCK", current_stock="2.000")
        resp = client.post(f"/orders/{pending_order['id']}/items", json={
            "product_id": low["id"],
            "quantity": "10.000",
            "unit_price": "5.00",
        }, headers=auth_headers)
        assert resp.status_code == 400
        assert "insufficient" in resp.json()["detail"].lower()

    def test_add_item_inactive_product_returns_400(self, client, auth_headers, pending_order, make_product):
        product = make_product(sku="INACTIVE-P", current_stock="50.000")
        client.put(f"/products/{product['id']}", json={"is_active": False}, headers=auth_headers)
        resp = client.post(f"/orders/{pending_order['id']}/items", json={
            "product_id": product["id"],
            "quantity": "1.000",
            "unit_price": "5.00",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_add_item_to_nonexistent_order_returns_400(self, client, auth_headers, product):
        # The router catches ValueError from the service and returns 400
        resp = client.post("/orders/9999/items", json={
            "product_id": product["id"],
            "quantity": "1.000",
            "unit_price": "5.00",
        }, headers=auth_headers)
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"].lower()


class TestRemoveItem:
    def test_remove_item_from_pending_order(self, client, auth_headers, pending_order, product):
        add_resp = client.post(f"/orders/{pending_order['id']}/items", json={
            "product_id": product["id"],
            "quantity": "1.000",
            "unit_price": "10.00",
        }, headers=auth_headers)
        item_id = add_resp.json()["items"][0]["id"]

        resp = client.delete(f"/orders/{pending_order['id']}/items/{item_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["items"] == []


class TestDeleteOrder:
    def test_delete_pending_order(self, client, auth_headers, pending_order):
        resp = client.delete(f"/orders/{pending_order['id']}", headers=auth_headers)
        assert resp.status_code == 204

    def test_delete_nonpending_order_returns_400(self, client, auth_headers, pending_order, product):
        # Add item and advance to processing
        client.post(f"/orders/{pending_order['id']}/items", json={
            "product_id": product["id"],
            "quantity": "1.000",
            "unit_price": "10.00",
        }, headers=auth_headers)
        client.post(f"/orders/{pending_order['id']}/advance", headers=auth_headers)
        resp = client.delete(f"/orders/{pending_order['id']}", headers=auth_headers)
        assert resp.status_code == 400


class TestAdvanceStatus:
    def test_advance_pending_to_processing_deducts_stock(self, client, auth_headers, pending_order, product):
        client.post(f"/orders/{pending_order['id']}/items", json={
            "product_id": product["id"],
            "quantity": "5.000",
            "unit_price": "10.00",
        }, headers=auth_headers)

        resp = client.post(f"/orders/{pending_order['id']}/advance", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "processing"

        # Verify stock was deducted
        product_resp = client.get(f"/products/{product['id']}", headers=auth_headers)
        assert float(product_resp.json()["current_stock"]) == 95.0

    def test_advance_pending_to_processing_creates_exit_movement(self, client, auth_headers, pending_order, product, db):
        from app.models.stock_movement import StockMovement, MovementType
        client.post(f"/orders/{pending_order['id']}/items", json={
            "product_id": product["id"],
            "quantity": "3.000",
            "unit_price": "10.00",
        }, headers=auth_headers)
        client.post(f"/orders/{pending_order['id']}/advance", headers=auth_headers)

        movement = db.query(StockMovement).filter(
            StockMovement.order_id == pending_order["id"],
            StockMovement.type == MovementType.exit,
        ).first()
        assert movement is not None
        assert float(movement.quantity) == 3.0

    def test_advance_status_chain(self, client, auth_headers, pending_order, product):
        client.post(f"/orders/{pending_order['id']}/items", json={
            "product_id": product["id"],
            "quantity": "1.000",
            "unit_price": "10.00",
        }, headers=auth_headers)

        statuses = []
        for _ in range(3):
            r = client.post(f"/orders/{pending_order['id']}/advance", headers=auth_headers)
            statuses.append(r.json()["status"])

        assert statuses == ["processing", "shipped", "delivered"]

    def test_advance_delivered_order_returns_400(self, client, auth_headers, pending_order, product):
        client.post(f"/orders/{pending_order['id']}/items", json={
            "product_id": product["id"],
            "quantity": "1.000",
            "unit_price": "10.00",
        }, headers=auth_headers)
        for _ in range(3):
            client.post(f"/orders/{pending_order['id']}/advance", headers=auth_headers)

        resp = client.post(f"/orders/{pending_order['id']}/advance", headers=auth_headers)
        assert resp.status_code == 400

    def test_advance_empty_order_returns_400(self, client, auth_headers, pending_order):
        resp = client.post(f"/orders/{pending_order['id']}/advance", headers=auth_headers)
        assert resp.status_code == 400
        assert "no items" in resp.json()["detail"].lower()

    def test_advance_insufficient_stock_at_processing_returns_400(self, client, auth_headers, pending_order, make_product, db):
        from app.models.product import Product
        product = make_product(sku="THIN-STOCK", current_stock="5.000")
        client.post(f"/orders/{pending_order['id']}/items", json={
            "product_id": product["id"],
            "quantity": "5.000",
            "unit_price": "10.00",
        }, headers=auth_headers)

        # Manually drain the stock so it fails at advance time
        p = db.get(Product, product["id"])
        p.current_stock = 0
        db.commit()

        resp = client.post(f"/orders/{pending_order['id']}/advance", headers=auth_headers)
        assert resp.status_code == 400
