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

    def test_rango_invertido_da_400_con_mensaje_claro(self, client, auth_headers, product_with_stock):
        """
        Antes un rango invertido devolvía una lista vacía sin ningún aviso y
        parecía que simplemente no había movimientos.
        """
        resp = client.get(
            "/stock-movements?date_from=2024-12-31T00:00:00&date_to=2024-01-01T00:00:00",
            headers=auth_headers,
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert isinstance(detail, str)
        assert "desde" in detail and "hasta" in detail
        assert resp.json()["errors"]["date_from"]

    def test_fecha_desde_en_el_futuro_da_400(self, client, auth_headers, product_with_stock):
        resp = client.get(
            "/stock-movements?date_from=2999-01-01T00:00:00", headers=auth_headers
        )
        assert resp.status_code == 400
        assert "futuro" in resp.json()["detail"]

    def test_hasta_lejano_es_valido(self, client, auth_headers, product_with_stock):
        # Un "hasta" lejano es solo un límite superior abierto, no un error.
        resp = client.get(
            "/stock-movements?date_to=2999-12-31T23:59:59", headers=auth_headers
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_rango_con_extremos_iguales_es_valido(self, client, auth_headers, product_with_stock):
        resp = client.get(
            "/stock-movements?date_from=2024-01-01T00:00:00&date_to=2024-01-01T00:00:00",
            headers=auth_headers,
        )
        assert resp.status_code == 200

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

    def test_el_detalle_marca_las_lineas_omitidas_de_la_factura(
        self, client, auth_headers, mocker, make_product, db
    ):
        """
        El detalle del movimiento es la pantalla de trazabilidad: es donde se
        mira para saber qué pasó con cada línea de la factura.

        El esquema de esta respuesta no incluía `skipped`, así que las líneas
        que el usuario había omitido al confirmar llegaban sin la marca y la
        interfaz las mostraba como «Sumada al stock». El stock estaba bien —la
        línea no lo tocaba—, pero el detalle decía justo lo contrario.
        """
        from tests.test_invoices import _upload_invoice
        from app.models.stock_movement import StockMovement

        producto = make_product(sku="OMIT-P1", name="Blue Widget", current_stock="0.000")
        procesada = _upload_invoice(client, auth_headers, mocker).json()

        azul = next(i for i in procesada["items"] if "Blue Widget" in i["description"])
        rojo = next(i for i in procesada["items"] if "Red Gadget" in i["description"])

        confirmacion = client.post(
            f"/invoices/{procesada['invoice_id']}/confirm",
            json={"items": [
                {"invoice_item_id": azul["id"], "product_id": producto["id"]},
                {"invoice_item_id": rojo["id"], "skip": True},
            ]},
            headers=auth_headers,
        )
        assert confirmacion.status_code == 200, confirmacion.text

        movimiento = (
            db.query(StockMovement)
            .filter(StockMovement.invoice_id == procesada["invoice_id"])
            .first()
        )
        assert movimiento is not None, "la línea no omitida debe generar un movimiento"

        resp = client.get(f"/stock-movements/{movimiento.id}", headers=auth_headers)
        assert resp.status_code == 200
        lineas = {i["description"]: i for i in resp.json()["invoice"]["items"]}

        assert lineas["Red Gadget"]["skipped"] is True, "la omitida debe venir marcada"
        assert lineas["Blue Widget"]["skipped"] is False

        # Y la omisión tiene que ser real, no solo una etiqueta.
        movimientos = client.get("/stock-movements", headers=auth_headers).json()
        assert all(
            m["product"]["sku"] != "RED-GADGET" for m in movimientos
        ), "una línea omitida no puede generar movimiento de stock"


class TestAislamientoDeMovimientos:
    def test_no_se_listan_movimientos_de_otra_organizacion(
        self, client, other_org_headers, product_with_stock
    ):
        assert client.get("/stock-movements", headers=other_org_headers).json() == []

    def test_no_se_accede_a_un_movimiento_ajeno(
        self, client, other_org_headers, product_with_stock, db
    ):
        from app.models.stock_movement import StockMovement

        movement = db.query(StockMovement).first()
        resp = client.get(f"/stock-movements/{movement.id}", headers=other_org_headers)
        assert resp.status_code == 404
