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
        resp = client.post(
            "/customers", json={"name": "Equis", "email": "x@x.com", "phone": "555-0000"}
        )
        assert resp.status_code == 401

    def test_create_customer_invalid_email_returns_422(self, client, auth_headers):
        resp = client.post("/customers", json={
            "name": "Bad Email",
            "email": "not-an-email",
            "phone": "555-0000",
        }, headers=auth_headers)
        assert resp.status_code == 422
        cuerpo = resp.json()
        # El detail siempre es un string: si fuera una lista de objetos, el
        # frontend se quedaba en blanco al renderizarlo.
        assert isinstance(cuerpo["detail"], str)
        assert "email" in cuerpo["errors"]

    def test_nombre_con_numeros_da_422(self, client, auth_headers):
        resp = client.post("/customers", json={
            "name": "Cliente 123",
            "email": "num@test.com",
            "phone": "555-0000",
        }, headers=auth_headers)
        assert resp.status_code == 422
        assert "números" in resp.json()["errors"]["name"]

    def test_telefono_invalido_da_422(self, client, auth_headers):
        resp = client.post("/customers", json={
            "name": "Sin Telefono",
            "email": "tel@test.com",
            "phone": "abc",
        }, headers=auth_headers)
        assert resp.status_code == 422
        assert "phone" in resp.json()["errors"]

    def test_nombre_con_solo_espacios_da_422(self, client, auth_headers):
        resp = client.post("/customers", json={
            "name": "    ",
            "email": "espacios@test.com",
            "phone": "555-0000",
        }, headers=auth_headers)
        assert resp.status_code == 422
        assert "name" in resp.json()["errors"]


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


class TestAislamientoDeClientes:
    def test_no_se_listan_clientes_de_otra_organizacion(
        self, client, other_org_headers, make_customer
    ):
        make_customer(name="Cliente Propio", email="propio@test.com")
        assert client.get("/customers", headers=other_org_headers).json() == []

    def test_no_se_accede_a_un_cliente_ajeno(
        self, client, other_org_headers, make_customer
    ):
        customer = make_customer()
        assert (
            client.get(f"/customers/{customer['id']}", headers=other_org_headers).status_code
            == 404
        )

    def test_el_mismo_correo_puede_repetirse_en_otra_organizacion(
        self, client, auth_headers, other_org_headers
    ):
        payload = {
            "name": "Cliente Compartido",
            "email": "compartido@test.com",
            "phone": "555-7777",
        }
        assert client.post("/customers", json=payload, headers=auth_headers).status_code == 201
        assert (
            client.post("/customers", json=payload, headers=other_org_headers).status_code == 201
        )

    def test_no_se_ve_el_historial_de_un_cliente_ajeno(
        self, client, other_org_headers, make_customer
    ):
        customer = make_customer()
        resp = client.get(f"/customers/{customer['id']}/orders", headers=other_org_headers)
        assert resp.status_code == 404


class TestBorradoDeClienteConPedidos:
    """
    Un cliente con pedidos no se puede borrar. Antes el intento llegaba hasta
    la base y volvía como violación de integridad: el usuario leía un mensaje
    genérico sobre "información relacionada" que no nombraba los pedidos.
    """

    def test_no_se_borra_y_el_mensaje_nombra_los_pedidos(
        self, client, auth_headers, make_customer, make_product
    ):
        customer = make_customer()
        producto = make_product(sku="DEL-C1", current_stock="10.000")
        pedido = client.post(
            "/orders", json={"customer_id": customer["id"]}, headers=auth_headers
        ).json()
        client.post(f"/orders/{pedido['id']}/items", json={
            "product_id": producto["id"], "quantity": "1.000", "unit_price": "10.00",
        }, headers=auth_headers)

        resp = client.delete(f"/customers/{customer['id']}", headers=auth_headers)
        assert resp.status_code == 409
        detalle = resp.json()["detail"]
        assert "pedido" in detalle
        assert "información relacionada" not in detalle
        # El cliente sigue existiendo.
        assert client.get(f"/customers/{customer['id']}", headers=auth_headers).status_code == 200

    def test_el_listado_avisa_que_no_se_puede_borrar(
        self, client, auth_headers, make_customer
    ):
        customer = make_customer()
        # Sin pedidos se puede borrar y no hay motivo que mostrar.
        libre = client.get("/customers", headers=auth_headers).json()[0]
        assert libre["can_delete"] is True
        assert libre["delete_blocked_reason"] is None

        client.post("/orders", json={"customer_id": customer["id"]}, headers=auth_headers)

        bloqueado = client.get("/customers", headers=auth_headers).json()[0]
        assert bloqueado["can_delete"] is False
        assert "pedido" in bloqueado["delete_blocked_reason"]
