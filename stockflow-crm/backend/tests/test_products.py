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
        # El router responde 400 (no 409) ante un SKU repetido.
        payload = {"sku": "DUP-SKU", "name": "Product A", "price": "1.00"}
        client.post("/products", json=payload, headers=auth_headers)
        resp = client.post("/products", json={"sku": "DUP-SKU", "name": "Product B", "price": "2.00"}, headers=auth_headers)
        assert resp.status_code == 400
        assert "ya existe" in resp.json()["detail"].lower()
        assert resp.json()["errors"]["sku"]

    def test_el_mismo_sku_puede_repetirse_en_otra_organizacion(
        self, client, auth_headers, other_org_headers
    ):
        payload = {"sku": "COMPARTIDO-1", "name": "Producto", "price": "1.00"}
        assert client.post("/products", json=payload, headers=auth_headers).status_code == 201
        # El SKU dejó de ser único a nivel global: cada organización tiene el suyo.
        assert client.post("/products", json=payload, headers=other_org_headers).status_code == 201

    def test_create_product_requires_auth(self, client):
        resp = client.post("/products", json={"sku": "X", "name": "X", "price": "1.00"})
        assert resp.status_code == 401


class TestValidacionesDeProducto:
    def test_nombre_de_producto_admite_numeros(self, client, auth_headers):
        # A diferencia del nombre de una persona: "Coca Cola 500ml" es válido.
        resp = client.post("/products", json={
            "sku": "COLA-500",
            "name": "Coca Cola 500ml",
            "price": "1200.00",
        }, headers=auth_headers)
        assert resp.status_code == 201

    def test_nombre_vacio_da_422_con_mensaje_legible(self, client, auth_headers):
        resp = client.post("/products", json={
            "sku": "VACIO-1", "name": "   ", "price": "1.00",
        }, headers=auth_headers)
        assert resp.status_code == 422
        cuerpo = resp.json()
        assert isinstance(cuerpo["detail"], str)
        assert "name" in cuerpo["errors"]

    def test_sku_con_espacios_da_422(self, client, auth_headers):
        resp = client.post("/products", json={
            "sku": "CON ESPACIO", "name": "Producto", "price": "1.00",
        }, headers=auth_headers)
        assert resp.status_code == 422
        assert "sku" in resp.json()["errors"]

    def test_precio_desmedido_da_422_y_no_error_de_servidor(self, client, auth_headers):
        """
        Un importe mayor al que admite la columna llegaba hasta PostgreSQL y
        volvía como error 500. Tiene que frenarse en la validación.
        """
        resp = client.post("/products", json={
            "sku": "ENORME-1", "name": "Producto", "price": "99999999999999999999.00",
        }, headers=auth_headers)
        assert resp.status_code == 422, "no debe llegar a la base ni dar 500"
        assert "price" in resp.json()["errors"]

    def test_stock_desmedido_da_422(self, client, auth_headers):
        resp = client.post("/products", json={
            "sku": "ENORME-2", "name": "Producto", "price": "1.00",
            "current_stock": "99999999999999999999",
        }, headers=auth_headers)
        assert resp.status_code == 422
        assert "current_stock" in resp.json()["errors"]

    def test_precio_negativo_da_422(self, client, auth_headers):
        resp = client.post("/products", json={
            "sku": "NEG-1", "name": "Producto", "price": "-5.00",
        }, headers=auth_headers)
        assert resp.status_code == 422
        assert "price" in resp.json()["errors"]


class TestStockDecimal:
    def test_stock_decimal_rechazado_por_defecto(self, client, auth_headers):
        # "3.5 teclados" es un error de integridad para un producto unitario.
        resp = client.post("/products", json={
            "sku": "UNIDAD-1",
            "name": "Teclado",
            "price": "100.00",
            "current_stock": "3.500",
        }, headers=auth_headers)
        assert resp.status_code == 422
        assert isinstance(resp.json()["detail"], str)

    def test_stock_decimal_permitido_si_es_a_granel(self, client, auth_headers):
        resp = client.post("/products", json={
            "sku": "GRANEL-1",
            "name": "Harina",
            "price": "800.00",
            "current_stock": "3.500",
            "allow_decimal_stock": True,
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["allow_decimal_stock"] is True
        assert float(resp.json()["current_stock"]) == 3.5

    def test_ajustar_a_decimal_un_producto_unitario_da_error(
        self, client, auth_headers, make_product
    ):
        product = make_product(sku="UNIDAD-2", current_stock="10.000")
        resp = client.put(
            f"/products/{product['id']}",
            json={"current_stock": "7.250"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "enteras" in resp.json()["detail"]

    def test_no_se_puede_quitar_el_flag_con_stock_decimal(self, client, auth_headers):
        creado = client.post("/products", json={
            "sku": "GRANEL-2",
            "name": "Azúcar",
            "price": "500.00",
            "current_stock": "2.500",
            "allow_decimal_stock": True,
        }, headers=auth_headers).json()

        resp = client.put(
            f"/products/{creado['id']}",
            json={"allow_decimal_stock": False},
            headers=auth_headers,
        )
        assert resp.status_code == 400


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

    def test_no_se_puede_borrar_con_stock_pendiente(self, client, auth_headers, make_product):
        product = make_product(current_stock="10.000")
        resp = client.delete(f"/products/{product['id']}", headers=auth_headers)
        assert resp.status_code == 409
        assert "stock" in resp.json()["detail"].lower()

    def test_se_puede_borrar_tras_ajustar_el_stock_a_cero(
        self, client, auth_headers, make_product
    ):
        """
        Este era el defecto reportado: un producto con stock 0 y sin operaciones
        comerciales no se podía eliminar. El alta y los ajustes manuales generan
        movimientos internos del sistema que bloqueaban el borrado para siempre.
        """
        product = make_product(sku="CICLO-1", current_stock="10.000")
        # Alta con stock (movimiento de entrada) + ajuste a 0 (movimiento de ajuste).
        client.put(
            f"/products/{product['id']}", json={"current_stock": "0.000"}, headers=auth_headers
        )

        detalle = client.get(f"/products/{product['id']}", headers=auth_headers).json()
        assert detalle["can_delete"] is True
        assert detalle["delete_blocked_reason"] is None

        assert client.delete(f"/products/{product['id']}", headers=auth_headers).status_code == 204

    def test_los_movimientos_internos_se_borran_con_el_producto(
        self, client, auth_headers, make_product, db
    ):
        from app.models.stock_movement import StockMovement

        product = make_product(sku="CICLO-2", current_stock="5.000")
        client.put(
            f"/products/{product['id']}", json={"current_stock": "0.000"}, headers=auth_headers
        )
        client.delete(f"/products/{product['id']}", headers=auth_headers)

        restantes = (
            db.query(StockMovement).filter(StockMovement.product_id == product["id"]).count()
        )
        assert restantes == 0

    def test_no_se_puede_borrar_con_historial_de_pedidos(
        self, client, auth_headers, make_product, make_customer
    ):
        product = make_product(sku="VENDIDO-1", current_stock="10.000")
        customer = make_customer()
        order = client.post(
            "/orders", json={"customer_id": customer["id"]}, headers=auth_headers
        ).json()
        client.post(
            f"/orders/{order['id']}/items",
            json={"product_id": product["id"], "quantity": "10.000", "unit_price": "10.00"},
            headers=auth_headers,
        )
        # Se descuenta todo el stock, así que el bloqueo no puede venir del stock.
        client.post(f"/orders/{order['id']}/advance", headers=auth_headers)

        detalle = client.get(f"/products/{product['id']}", headers=auth_headers).json()
        assert float(detalle["current_stock"]) == 0
        assert detalle["can_delete"] is False
        assert "pedido" in detalle["delete_blocked_reason"].lower()

        resp = client.delete(f"/products/{product['id']}", headers=auth_headers)
        assert resp.status_code == 409

    def test_delete_nonexistent_product_returns_404(self, client, auth_headers):
        resp = client.delete("/products/9999", headers=auth_headers)
        assert resp.status_code == 404


class TestAislamientoEntreOrganizaciones:
    def test_no_se_listan_productos_de_otra_organizacion(
        self, client, auth_headers, other_org_headers, make_product
    ):
        make_product(sku="MIO-1", name="Producto propio")
        ajenos = client.get("/products", headers=other_org_headers).json()
        assert ajenos == []

    def test_no_se_accede_por_id_a_un_producto_ajeno(
        self, client, auth_headers, other_org_headers, make_product
    ):
        product = make_product(sku="MIO-2")
        # 404 en lugar de 403: confirmar que existe ya sería filtrar información.
        resp = client.get(f"/products/{product['id']}", headers=other_org_headers)
        assert resp.status_code == 404

    def test_no_se_modifica_un_producto_ajeno(
        self, client, auth_headers, other_org_headers, make_product
    ):
        product = make_product(sku="MIO-3")
        resp = client.put(
            f"/products/{product['id']}", json={"name": "Robado"}, headers=other_org_headers
        )
        assert resp.status_code == 404

    def test_no_se_elimina_un_producto_ajeno(
        self, client, auth_headers, other_org_headers, make_product
    ):
        product = make_product(sku="MIO-4", current_stock="0.000")
        assert (
            client.delete(f"/products/{product['id']}", headers=other_org_headers).status_code
            == 404
        )
