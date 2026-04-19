"""Integration tests for /customers routes."""
import pytest


class TestCreateCustomer:
    def test_create_customer_success(self, client, auth_headers):
        resp = client.post("/customers", json={
            "name": "Alice Smith",
            "email": "alice@test.com",
            "phone": "555-1234",
            "address": "123 Main St",
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Alice Smith"
        assert data["email"] == "alice@test.com"

    def test_create_customer_without_optional_fields(self, client, auth_headers):
        resp = client.post("/customers", json={
            "name": "Bob Jones",
            "email": "bob@test.com",
            "phone": "555-5678",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["address"] is None

    def test_create_customer_requires_auth(self, client):
        resp = client.post("/customers", json={"name": "X", "email": "x@x.com", "phone": "1"})
        assert resp.status_code == 401

    def test_create_customer_invalid_email_returns_422(self, client, auth_headers):
        resp = client.post("/customers", json={
            "name": "Bad Email",
            "email": "not-an-email",
            "phone": "555-0000",
        }, headers=auth_headers)
        assert resp.status_code == 422


class TestListCustomers:
    def test_list_customers_empty(self, client, auth_headers):
        resp = client.get("/customers", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_customers_returns_all(self, client, auth_headers, make_customer):
        make_customer(name="Alpha", email="alpha@test.com")
        make_customer(name="Beta", email="beta@test.com")
        resp = client.get("/customers", headers=auth_headers)
        assert len(resp.json()) == 2

    def test_list_customers_ordered_by_name(self, client, auth_headers, make_customer):
        make_customer(name="Zoe", email="z@test.com")
        make_customer(name="Anna", email="a@test.com")
        names = [c["name"] for c in client.get("/customers", headers=auth_headers).json()]
        assert names == sorted(names)


class TestGetCustomer:
    def test_get_existing_customer(self, client, auth_headers, make_customer):
        created = make_customer()
        resp = client.get(f"/customers/{created['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_nonexistent_customer_returns_404(self, client, auth_headers):
        resp = client.get("/customers/9999", headers=auth_headers)
        assert resp.status_code == 404


class TestUpdateCustomer:
    def test_update_customer_name_and_phone(self, client, auth_headers, make_customer):
        customer = make_customer()
        resp = client.put(f"/customers/{customer['id']}", json={
            "name": "Updated Name",
            "phone": "555-9999",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"
        assert resp.json()["phone"] == "555-9999"

    def test_update_nonexistent_customer_returns_404(self, client, auth_headers):
        resp = client.put("/customers/9999", json={"name": "Ghost"}, headers=auth_headers)
        assert resp.status_code == 404


class TestDeleteCustomer:
    def test_delete_customer_success(self, client, auth_headers, make_customer):
        customer = make_customer()
        resp = client.delete(f"/customers/{customer['id']}", headers=auth_headers)
        assert resp.status_code == 204
        assert client.get(f"/customers/{customer['id']}", headers=auth_headers).status_code == 404

    def test_delete_nonexistent_customer_returns_404(self, client, auth_headers):
        resp = client.delete("/customers/9999", headers=auth_headers)
        assert resp.status_code == 404


class TestCustomerOrderHistory:
    def test_order_history_empty(self, client, auth_headers, make_customer):
        customer = make_customer()
        resp = client.get(f"/customers/{customer['id']}/orders", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["customer"]["id"] == customer["id"]
        assert data["orders"] == []

    def test_order_history_includes_orders(self, client, auth_headers, make_customer, make_product):
        customer = make_customer()
        product = make_product(sku="HIST-001", current_stock="50.000")

        order_resp = client.post("/orders", json={"customer_id": customer["id"]}, headers=auth_headers)
        order_id = order_resp.json()["id"]
        client.post(f"/orders/{order_id}/items", json={
            "product_id": product["id"],
            "quantity": "2.000",
            "unit_price": "10.00",
        }, headers=auth_headers)

        resp = client.get(f"/customers/{customer['id']}/orders", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["orders"]) == 1
        assert float(resp.json()["orders"][0]["total"]) == 20.0
