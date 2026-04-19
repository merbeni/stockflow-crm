"""Integration tests for /stock-movements routes."""
import pytest


@pytest.fixture
def product_with_stock(make_product):
    return make_product(sku="SM-P1", current_stock="50.000", minimum_stock="5.000")


class TestListMovements:
    def test_list_movements_empty_initially(self, client, auth_headers, make_product):
        make_product(sku="EMPTY-P1", current_stock="0.000")
        resp = client.get("/stock-movements", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_movements_shows_initial_entry(self, client, auth_headers, product_with_stock):
        resp = client.get("/stock-movements", headers=auth_headers)
        assert resp.status_code == 200
        movements = resp.json()
        assert len(movements) == 1
        assert movements[0]["type"] == "entry"

    def test_filter_by_type_entry(self, client, auth_headers, product_with_stock):
        resp = client.get("/stock-movements?type=entry", headers=auth_headers)
        movements = resp.json()
        assert all(m["type"] == "entry" for m in movements)

    def test_filter_by_type_exit_empty(self, client, auth_headers, product_with_stock):
        resp = client.get("/stock-movements?type=exit", headers=auth_headers)
        assert resp.json() == []

    def test_filter_by_type_adjustment(self, client, auth_headers, product_with_stock):
        client.put(
            f"/products/{product_with_stock['id']}",
            json={"current_stock": "60.000"},
            headers=auth_headers,
        )
        resp = client.get("/stock-movements?type=adjustment", headers=auth_headers)
        movements = resp.json()
        assert len(movements) == 1
        assert movements[0]["type"] == "adjustment"

    def test_filter_by_product_id(self, client, auth_headers, make_product):
        p1 = make_product(sku="FILTER-P1", current_stock="10.000")
        make_product(sku="FILTER-P2", current_stock="20.000")
        resp = client.get(f"/stock-movements?product_id={p1['id']}", headers=auth_headers)
        movements = resp.json()
        assert all(m["product"]["id"] == p1["id"] for m in movements)

    def test_filter_by_date_range(self, client, auth_headers, product_with_stock):
        resp = client.get(
            "/stock-movements?date_from=2020-01-01T00:00:00&date_to=2099-12-31T23:59:59",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_pagination_limit(self, client, auth_headers, make_product):
        for i in range(5):
            make_product(sku=f"PAG-P{i}", current_stock="10.000")
        resp = client.get("/stock-movements?limit=3", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) <= 3

    def test_requires_auth(self, client):
        resp = client.get("/stock-movements")
        assert resp.status_code == 401


class TestGetMovement:
    def test_get_existing_movement(self, client, auth_headers, product_with_stock, db):
        from app.models.stock_movement import StockMovement
        movement = db.query(StockMovement).first()
        assert movement is not None

        resp = client.get(f"/stock-movements/{movement.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == movement.id
        assert resp.json()["type"] == "entry"

    def test_get_nonexistent_movement_returns_404(self, client, auth_headers):
        resp = client.get("/stock-movements/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_movement_linked_to_order(self, client, auth_headers, make_customer, make_product, db):
        from app.models.stock_movement import StockMovement, MovementType
        customer = make_customer()
        product = make_product(sku="ORD-SM-P1", current_stock="20.000")

        order_resp = client.post("/orders", json={"customer_id": customer["id"]}, headers=auth_headers)
        order_id = order_resp.json()["id"]
        client.post(f"/orders/{order_id}/items", json={
            "product_id": product["id"],
            "quantity": "5.000",
            "unit_price": "10.00",
        }, headers=auth_headers)
        client.post(f"/orders/{order_id}/advance", headers=auth_headers)

        movement = db.query(StockMovement).filter(
            StockMovement.order_id == order_id,
            StockMovement.type == MovementType.exit,
        ).first()
        assert movement is not None

        resp = client.get(f"/stock-movements/{movement.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["order_id"] == order_id
