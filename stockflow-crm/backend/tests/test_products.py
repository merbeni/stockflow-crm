"""Integration tests for /products routes and product service business logic."""
import pytest


class TestCreateProduct:
    def test_create_product_success(self, client, auth_headers):
        resp = client.post("/products", json={
            "sku": "WIDGET-01",
            "name": "Blue Widget",
            "price": "9.99",
            "current_stock": "100.000",
            "minimum_stock": "10.000",
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["sku"] == "WIDGET-01"
        assert data["name"] == "Blue Widget"
        assert float(data["price"]) == 9.99
        assert float(data["current_stock"]) == 100.0
        assert data["is_active"] is True

    def test_create_product_creates_initial_stock_movement(self, client, auth_headers, db):
        from app.models.stock_movement import StockMovement, MovementType
        resp = client.post("/products", json={
            "sku": "WIDGET-02",
            "name": "Red Widget",
            "price": "5.00",
            "current_stock": "25.000",
        }, headers=auth_headers)
        assert resp.status_code == 201
        product_id = resp.json()["id"]

        movement = db.query(StockMovement).filter(
            StockMovement.product_id == product_id
        ).first()
        assert movement is not None
        assert movement.type == MovementType.entry
        assert float(movement.quantity) == 25.0

    def test_create_product_zero_stock_no_movement(self, client, auth_headers, db):
        from app.models.stock_movement import StockMovement
        resp = client.post("/products", json={
            "sku": "WIDGET-03",
            "name": "Empty Widget",
            "price": "5.00",
            "current_stock": "0.000",
        }, headers=auth_headers)
        assert resp.status_code == 201
        product_id = resp.json()["id"]
        count = db.query(StockMovement).filter(StockMovement.product_id == product_id).count()
        assert count == 0

    def test_create_product_duplicate_sku_returns_400(self, client, auth_headers):
        # The router returns 400 (not 409) for duplicate SKU
        payload = {"sku": "DUP-SKU", "name": "Product A", "price": "1.00"}
        client.post("/products", json=payload, headers=auth_headers)
        resp = client.post("/products", json={"sku": "DUP-SKU", "name": "Product B", "price": "2.00"}, headers=auth_headers)
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"].lower()

    def test_create_product_requires_auth(self, client):
        resp = client.post("/products", json={"sku": "X", "name": "X", "price": "1.00"})
        assert resp.status_code == 401


class TestListProducts:
    def test_list_products_empty(self, client, auth_headers):
        resp = client.get("/products", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_products_returns_all(self, client, auth_headers, make_product):
        make_product(sku="A-001", name="Alpha")
        make_product(sku="B-001", name="Beta")
        resp = client.get("/products", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_products_low_stock_filter(self, client, auth_headers, make_product):
        make_product(sku="LOW-001", name="Low", current_stock="2.000", minimum_stock="10.000")
        make_product(sku="OK-001", name="OK", current_stock="50.000", minimum_stock="5.000")
        resp = client.get("/products?low_stock_only=true", headers=auth_headers)
        assert resp.status_code == 200
        names = [p["name"] for p in resp.json()]
        assert "Low" in names
        assert "OK" not in names

    def test_low_stock_field_computed_correctly(self, client, auth_headers, make_product):
        make_product(sku="LOW-X", name="LowX", current_stock="3.000", minimum_stock="10.000")
        resp = client.get("/products", headers=auth_headers)
        product = next(p for p in resp.json() if p["sku"] == "LOW-X")
        assert product["low_stock"] is True


class TestGetProduct:
    def test_get_existing_product(self, client, auth_headers, make_product):
        created = make_product()
        resp = client.get(f"/products/{created['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_nonexistent_product_returns_404(self, client, auth_headers):
        resp = client.get("/products/9999", headers=auth_headers)
        assert resp.status_code == 404


class TestUpdateProduct:
    def test_update_product_name_and_price(self, client, auth_headers, make_product):
        product = make_product()
        resp = client.put(f"/products/{product['id']}", json={
            "name": "Updated Name",
            "price": "19.99",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"
        assert float(resp.json()["price"]) == 19.99

    def test_update_stock_creates_adjustment_movement(self, client, auth_headers, make_product, db):
        from app.models.stock_movement import StockMovement, MovementType
        product = make_product(current_stock="50.000")
        client.put(f"/products/{product['id']}", json={"current_stock": "60.000"}, headers=auth_headers)

        movements = db.query(StockMovement).filter(
            StockMovement.product_id == product["id"],
            StockMovement.type == MovementType.adjustment,
        ).all()
        assert len(movements) == 1
        assert float(movements[0].quantity) == 10.0

    def test_update_stock_negative_adjustment(self, client, auth_headers, make_product, db):
        from app.models.stock_movement import StockMovement, MovementType
        product = make_product(current_stock="50.000")
        client.put(f"/products/{product['id']}", json={"current_stock": "30.000"}, headers=auth_headers)

        movement = db.query(StockMovement).filter(
            StockMovement.product_id == product["id"],
            StockMovement.type == MovementType.adjustment,
        ).first()
        assert float(movement.quantity) == -20.0

    def test_update_nonexistent_product_returns_404(self, client, auth_headers):
        resp = client.put("/products/9999", json={"name": "Ghost"}, headers=auth_headers)
        assert resp.status_code == 404


class TestDeleteProduct:
    def test_delete_product_success(self, client, auth_headers, make_product):
        product = make_product(sku="DEL-001", current_stock="0.000")
        resp = client.delete(f"/products/{product['id']}", headers=auth_headers)
        assert resp.status_code == 204
        assert client.get(f"/products/{product['id']}", headers=auth_headers).status_code == 404

    def test_delete_product_with_movements_returns_409(self, client, auth_headers, make_product):
        # Creating with non-zero stock creates a movement, so delete should fail
        product = make_product(current_stock="10.000")
        resp = client.delete(f"/products/{product['id']}", headers=auth_headers)
        assert resp.status_code == 409

    def test_delete_nonexistent_product_returns_404(self, client, auth_headers):
        resp = client.delete("/products/9999", headers=auth_headers)
        assert resp.status_code == 404
