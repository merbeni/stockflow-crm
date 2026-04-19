"""Integration tests for /suppliers routes."""
import pytest


class TestCreateSupplier:
    def test_create_supplier_success(self, client, auth_headers):
        resp = client.post("/suppliers", json={
            "name": "Acme Corp",
            "contact_name": "Road Runner",
            "email": "acme@test.com",
            "phone": "555-0100",
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Acme Corp"
        assert data["email"] == "acme@test.com"
        assert "id" in data

    def test_create_supplier_minimal_required_fields(self, client, auth_headers):
        # name, contact_name and email are required; phone is optional
        resp = client.post("/suppliers", json={
            "name": "Minimal Supplier",
            "contact_name": "Jane",
            "email": "jane@minimal.com",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["name"] == "Minimal Supplier"
        assert resp.json()["phone"] is None

    def test_create_supplier_missing_required_fields_returns_422(self, client, auth_headers):
        # Omitting contact_name and email should fail validation
        resp = client.post("/suppliers", json={"name": "Incomplete"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_supplier_requires_auth(self, client):
        resp = client.post("/suppliers", json={"name": "Anon"})
        assert resp.status_code == 401


class TestListSuppliers:
    def test_list_suppliers_empty(self, client, auth_headers):
        resp = client.get("/suppliers", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_suppliers_returns_all(self, client, auth_headers, make_supplier):
        make_supplier(name="Alpha Supplier", email="alpha@test.com")
        make_supplier(name="Beta Supplier", email="beta@test.com")
        resp = client.get("/suppliers", headers=auth_headers)
        assert len(resp.json()) == 2

    def test_list_suppliers_ordered_by_name(self, client, auth_headers, make_supplier):
        make_supplier(name="Zeta", email="z@test.com")
        make_supplier(name="Alpha", email="a@test.com")
        names = [s["name"] for s in client.get("/suppliers", headers=auth_headers).json()]
        assert names == sorted(names)


class TestGetSupplier:
    def test_get_existing_supplier(self, client, auth_headers, make_supplier):
        created = make_supplier()
        resp = client.get(f"/suppliers/{created['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_nonexistent_supplier_returns_404(self, client, auth_headers):
        resp = client.get("/suppliers/9999", headers=auth_headers)
        assert resp.status_code == 404


class TestUpdateSupplier:
    def test_update_supplier_name(self, client, auth_headers, make_supplier):
        supplier = make_supplier()
        resp = client.put(f"/suppliers/{supplier['id']}", json={"name": "New Name"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_update_nonexistent_supplier_returns_404(self, client, auth_headers):
        resp = client.put("/suppliers/9999", json={"name": "Ghost"}, headers=auth_headers)
        assert resp.status_code == 404


class TestDeleteSupplier:
    def test_delete_supplier_success(self, client, auth_headers, make_supplier):
        supplier = make_supplier()
        resp = client.delete(f"/suppliers/{supplier['id']}", headers=auth_headers)
        assert resp.status_code == 204
        assert client.get(f"/suppliers/{supplier['id']}", headers=auth_headers).status_code == 404

    def test_delete_nonexistent_supplier_returns_404(self, client, auth_headers):
        resp = client.delete("/suppliers/9999", headers=auth_headers)
        assert resp.status_code == 404
