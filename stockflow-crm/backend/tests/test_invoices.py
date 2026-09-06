"""Integration tests for /invoices routes — Gemini is always mocked."""
import json
import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

_FAKE_GEMINI_RESPONSE = {
    "is_invoice": True,
    "document_type": "factura de proveedor",
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

# Cabecera real de un PDF: el endpoint verifica el contenido del archivo y no
# solo el content_type declarado por el cliente.
_PDF_VALIDO = b"%PDF-1.4 contenido de prueba"


def _upload_invoice(client, auth_headers, mocker, gemini_data=None):
    """Sube un archivo de factura con la respuesta de Gemini simulada."""
    gemini_data = gemini_data or _FAKE_GEMINI_RESPONSE
    mocker.patch(
        "app.services.invoice.invoice_service.process_invoice_file",
        return_value=gemini_data,
    )
    resp = client.post(
        "/invoices/process",
        files={"file": ("invoice.pdf", _PDF_VALIDO, "application/pdf")},
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
        # Un ValueError del servicio (JSON ilegible) se traduce en un 422 con un
        # mensaje para el usuario; el texto crudo del modelo queda solo en el log.
        mocker.patch(
            "app.services.invoice.invoice_service.process_invoice_file",
            side_effect=ValueError("Gemini devolvió contenido que no es JSON: <html>..."),
        )
        resp = client.post(
            "/invoices/process",
            files={"file": ("invoice.pdf", _PDF_VALIDO, "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert isinstance(detail, str)
        # El detalle técnico no debe llegar al navegador.
        assert "Gemini" not in detail and "html" not in detail

    def _error_de_gemini(self, mocker, codigo, mensaje):
        """Simula un 4xx de Gemini sin construir la excepción a mano."""
        from google.genai.errors import ClientError

        error = ClientError.__new__(ClientError)
        error.code = codigo
        error.message = mensaje
        error.status = "INVALID_ARGUMENT"
        error.details = None
        error.response = None
        mocker.patch(
            "app.services.invoice.invoice_service.process_invoice_file",
            side_effect=error,
        )

    def test_documento_ilegible_da_422_y_no_error_de_servidor(
        self, client, auth_headers, mocker
    ):
        """
        Gemini responde 400 cuando el archivo no le sirve —un PDF dañado, vacío
        o protegido devuelve "The document has no pages"—. Ese ClientError no
        estaba capturado y escapaba como 500: el usuario veía "error del
        sistema" cuando el problema estaba en su archivo y podía resolverlo.
        """
        self._error_de_gemini(mocker, 400, "The document has no pages.")
        resp = client.post(
            "/invoices/process",
            files={"file": ("invoice.pdf", _PDF_VALIDO, "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 422, "un archivo ilegible no es una falla del servidor"
        detail = resp.json()["detail"]
        assert "dañado" in detail or "vacío" in detail
        # El texto de Google no debe llegar al navegador.
        assert "document has no pages" not in detail.lower()
        assert resp.json()["errors"].get("file")

    def test_cuota_de_gemini_agotada_se_trata_como_servicio_ocupado(
        self, client, auth_headers, mocker
    ):
        """Un 429 es "volvé a intentar", no un archivo mal: el frontend reintenta solo."""
        self._error_de_gemini(mocker, 429, "Resource has been exhausted.")
        resp = client.post(
            "/invoices/process",
            files={"file": ("invoice.pdf", _PDF_VALIDO, "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 503
        # El 503 le dice al frontend que reintente, pero el mensaje se muestra
        # tal cual si el reintento vuelve a fallar: acá viajaba el identificador
        # interno «gemini_unavailable» y era lo que terminaba leyendo la persona.
        detalle = resp.json()["detail"]
        assert "_" not in detalle
        assert "lectura automática" in detalle

    def test_un_corte_de_red_no_se_reporta_como_falla_del_sistema(
        self, client, auth_headers, mocker
    ):
        """
        Un fallo de transporte no es ni ServerError ni ClientError.

        Se escapaba de los dos bloques que atrapan los errores de Gemini y
        llegaba al usuario como un 500: la conexión con Google se había cortado
        —cosa que se arregla reintentando— y el sistema decía haberse roto.
        """
        import httpx

        mocker.patch(
            "app.services.invoice.invoice_service.process_invoice_file",
            side_effect=httpx.ReadError("connection aborted"),
        )
        resp = client.post(
            "/invoices/process",
            files={"file": ("invoice.pdf", _PDF_VALIDO, "application/pdf")},
            headers=auth_headers,
        )
        # 503 y no 500: es el código con el que el frontend reintenta solo.
        assert resp.status_code == 503
        detalle = resp.json()["detail"]
        assert "lectura automática" in detalle
        # El detalle técnico queda en el log, no en la pantalla.
        assert "connection aborted" not in detalle

    def test_un_tiempo_de_espera_agotado_recibe_el_mismo_trato(
        self, client, auth_headers, mocker
    ):
        import httpx

        mocker.patch(
            "app.services.invoice.invoice_service.process_invoice_file",
            side_effect=httpx.ReadTimeout("timed out"),
        )
        resp = client.post(
            "/invoices/process",
            files={"file": ("invoice.pdf", _PDF_VALIDO, "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 503

    def test_credenciales_mal_configuradas_no_culpan_al_usuario(
        self, client, auth_headers, mocker
    ):
        """Un 403 es un problema nuestro: no se le pide al usuario que corrija nada."""
        self._error_de_gemini(mocker, 403, "API key not valid.")
        resp = client.post(
            "/invoices/process",
            files={"file": ("invoice.pdf", _PDF_VALIDO, "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 502
        assert "API key" not in resp.json()["detail"]


class TestValidacionDeDocumento:
    """
    El defecto crítico reportado: el sistema aceptaba la foto de un gato como
    si fuera una factura y guardaba ítems inventados por la IA.
    """

    def test_documento_que_no_es_factura_se_rechaza(self, client, auth_headers, mocker):
        resp = _upload_invoice(
            client,
            auth_headers,
            mocker,
            gemini_data={
                "is_invoice": False,
                "document_type": "fotografía de un gato",
                "supplier": None,
                "date": None,
                "items": [],
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "no parece una factura" in detail
        assert "fotografía de un gato" in detail

    def test_documento_que_no_es_factura_no_guarda_nada(self, client, auth_headers, mocker, db):
        from app.models.invoice import Invoice

        _upload_invoice(
            client,
            auth_headers,
            mocker,
            gemini_data={
                "is_invoice": False,
                "document_type": "captura de pantalla",
                "items": [],
            },
        )
        # Antes se creaba la factura antes de cualquier control.
        assert db.query(Invoice).count() == 0
        assert client.get("/invoices", headers=auth_headers).json() == []

    def test_factura_sin_lineas_se_rechaza(self, client, auth_headers, mocker, db):
        from app.models.invoice import Invoice

        resp = _upload_invoice(
            client,
            auth_headers,
            mocker,
            gemini_data={"is_invoice": True, "supplier": "Acme", "items": []},
        )
        assert resp.status_code == 422
        assert "línea" in resp.json()["detail"]
        assert db.query(Invoice).count() == 0

    def test_archivo_con_extension_falsificada_se_rechaza(self, client, auth_headers):
        # El content_type lo declara el cliente: se comprueba el contenido real.
        resp = client.post(
            "/invoices/process",
            files={"file": ("virus.pdf", b"MZ\x90\x00 ejecutable", "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 415
        assert "contenido" in resp.json()["detail"]

    def test_imagen_valida_se_acepta(self, client, auth_headers, mocker):
        mocker.patch(
            "app.services.invoice.invoice_service.process_invoice_file",
            return_value=_FAKE_GEMINI_RESPONSE,
        )
        png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
        resp = client.post(
            "/invoices/process",
            files={"file": ("factura.png", png, "image/png")},
            headers=auth_headers,
        )
        assert resp.status_code == 201


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


class TestMensajesDeConfirmacion:
    """
    El evaluador vio "item 48: provide product_id", que además de ser
    incomprensible dejaba a la vista la estructura interna de la base.
    """

    def test_linea_sin_producto_da_un_mensaje_de_negocio(self, client, auth_headers, mocker):
        process_resp = _upload_invoice(client, auth_headers, mocker)
        invoice_id = process_resp.json()["invoice_id"]
        items = process_resp.json()["items"]

        resp = client.post(
            f"/invoices/{invoice_id}/confirm",
            json={"items": [{"invoice_item_id": items[0]["id"]}]},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert isinstance(detail, str)
        # Identifica la línea por su descripción, no por el ID interno.
        assert "Blue Widget" in detail
        assert "product_id" not in detail
        assert "new_product" not in detail
        assert str(items[0]["id"]) not in detail

    def test_producto_inexistente_no_expone_el_id(self, client, auth_headers, mocker):
        process_resp = _upload_invoice(client, auth_headers, mocker)
        invoice_id = process_resp.json()["invoice_id"]
        items = process_resp.json()["items"]

        resp = client.post(
            f"/invoices/{invoice_id}/confirm",
            json={"items": [{"invoice_item_id": items[0]["id"], "product_id": 99999}]},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "99999" not in resp.json()["detail"]

    def test_proveedor_inexistente_da_404_sin_id(self, client, auth_headers, mocker, make_product):
        product = make_product(sku="SUP-404", name="Blue Widget", current_stock="0.000")
        process_resp = _upload_invoice(client, auth_headers, mocker)
        invoice_id = process_resp.json()["invoice_id"]
        items = process_resp.json()["items"]

        resp = client.post(
            f"/invoices/{invoice_id}/confirm",
            json={
                "supplier_id": 99999,
                "items": [
                    {"invoice_item_id": items[0]["id"], "product_id": product["id"]},
                    {"invoice_item_id": items[1]["id"], "skip": True},
                ],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert "99999" not in resp.json()["detail"]

    def test_la_factura_sigue_pendiente_tras_un_error(self, client, auth_headers, mocker):
        process_resp = _upload_invoice(client, auth_headers, mocker)
        invoice_id = process_resp.json()["invoice_id"]
        items = process_resp.json()["items"]

        client.post(
            f"/invoices/{invoice_id}/confirm",
            json={"items": [{"invoice_item_id": items[0]["id"]}]},
            headers=auth_headers,
        )
        # Se puede volver a la revisión y corregir: la factura no queda bloqueada.
        detalle = client.get(f"/invoices/{invoice_id}", headers=auth_headers)
        assert detalle.json()["status"] == "pending"


class TestCorreccionesManuales:
    def test_se_puede_corregir_la_cantidad_extraida(
        self, client, auth_headers, mocker, make_product, db
    ):
        from app.models.product import Product

        product = make_product(sku="COR-001", name="Blue Widget", current_stock="0.000")
        process_resp = _upload_invoice(client, auth_headers, mocker)
        invoice_id = process_resp.json()["invoice_id"]
        items = process_resp.json()["items"]

        # La IA leyó 10; el usuario corrige a 7 antes de confirmar.
        resp = client.post(
            f"/invoices/{invoice_id}/confirm",
            json={
                "items": [
                    {
                        "invoice_item_id": items[0]["id"],
                        "product_id": product["id"],
                        "quantity": "7.000",
                        "unit_price": "6.50",
                        "description": "Widget azul (corregido)",
                    },
                    {"invoice_item_id": items[1]["id"], "skip": True},
                ]
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert float(db.get(Product, product["id"]).current_stock) == 7.0

        linea = next(i for i in resp.json()["items"] if not i["skipped"])
        assert linea["description"] == "Widget azul (corregido)"
        assert float(linea["unit_price"]) == 6.5

    def test_cantidad_decimal_rechazada_para_producto_unitario(
        self, client, auth_headers, mocker, make_product
    ):
        product = make_product(sku="COR-002", name="Blue Widget", current_stock="0.000")
        process_resp = _upload_invoice(client, auth_headers, mocker)
        invoice_id = process_resp.json()["invoice_id"]
        items = process_resp.json()["items"]

        resp = client.post(
            f"/invoices/{invoice_id}/confirm",
            json={
                "items": [
                    {
                        "invoice_item_id": items[0]["id"],
                        "product_id": product["id"],
                        "quantity": "7.500",
                    },
                    {"invoice_item_id": items[1]["id"], "skip": True},
                ]
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "enteras" in resp.json()["detail"]


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

    def test_reject_nonexistent_invoice_returns_404(self, client, auth_headers):
        resp = client.post("/invoices/9999/reject", headers=auth_headers)
        assert resp.status_code == 404
        assert "no encontramos" in resp.json()["detail"].lower()


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


class TestAislamientoDeFacturas:
    def test_no_se_listan_facturas_de_otra_organizacion(
        self, client, auth_headers, other_org_headers, mocker
    ):
        _upload_invoice(client, auth_headers, mocker)
        assert client.get("/invoices", headers=other_org_headers).json() == []

    def test_no_se_accede_a_una_factura_ajena(
        self, client, auth_headers, other_org_headers, mocker
    ):
        invoice_id = _upload_invoice(client, auth_headers, mocker).json()["invoice_id"]
        assert (
            client.get(f"/invoices/{invoice_id}", headers=other_org_headers).status_code == 404
        )

    def test_no_se_confirma_una_factura_ajena(
        self, client, auth_headers, other_org_headers, mocker
    ):
        resp_proceso = _upload_invoice(client, auth_headers, mocker)
        invoice_id = resp_proceso.json()["invoice_id"]
        items = resp_proceso.json()["items"]
        resp = client.post(
            f"/invoices/{invoice_id}/confirm",
            json={"items": [{"invoice_item_id": items[0]["id"], "skip": True}]},
            headers=other_org_headers,
        )
        assert resp.status_code == 404

    def test_no_se_sugieren_productos_de_otra_organizacion(
        self, client, auth_headers, other_org_headers, mocker
    ):
        # El producto existe en la organización A…
        client.post(
            "/products",
            json={"sku": "AJENO-1", "name": "Blue Widget", "price": "5.00"},
            headers=auth_headers,
        )
        # …pero la factura se procesa en la B y no debe sugerirlo.
        resp = _upload_invoice(client, other_org_headers, mocker)
        assert resp.status_code == 201
        for item in resp.json()["items"]:
            assert item["suggested_product_id"] is None


class TestRetomarUnaRevision:
    """
    La pantalla de revisión invita a dejarla para después («la factura queda
    pendiente hasta que la confirmes»). El emparejado automático se calculaba
    solo al procesar y viajaba únicamente en esa respuesta: quien volvía más
    tarde encontraba todas las líneas en blanco y tenía que rehacer a mano lo
    que el sistema ya había resuelto.
    """

    def test_la_factura_pendiente_conserva_las_sugerencias(
        self, client, auth_headers, mocker, make_product
    ):
        make_product(sku="BW-001", name="Blue Widget", current_stock="0.000")
        procesada = _upload_invoice(client, auth_headers, mocker)
        invoice_id = procesada.json()["invoice_id"]
        sugerido_al_procesar = procesada.json()["items"][0]["suggested_product_id"]
        assert sugerido_al_procesar is not None

        # Se vuelve más tarde, releyendo la factura guardada.
        resp = client.get(f"/invoices/{invoice_id}", headers=auth_headers)
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["suggested_product_id"] == sugerido_al_procesar
        assert item["suggested_product_name"] == "Blue Widget"

    def test_el_listado_no_las_calcula(
        self, client, auth_headers, mocker, make_product
    ):
        """
        El listado se mantiene barato.

        Calcular las sugerencias ahí obligaría a consultar la base por cada
        línea de cada factura pendiente, y solo hacen falta al abrir una para
        revisarla: la pantalla vuelve a pedir esa factura en ese momento.
        """
        make_product(sku="BW-001", name="Blue Widget", current_stock="0.000")
        _upload_invoice(client, auth_headers, mocker)

        facturas = client.get("/invoices", headers=auth_headers).json()
        assert facturas[0]["items"][0]["suggested_product_id"] is None

    def test_una_factura_ya_confirmada_no_sugiere_nada(
        self, client, auth_headers, mocker, make_product
    ):
        """La decisión ya está tomada: sugerir ahí solo confundiría."""
        product = make_product(sku="BW-001", name="Blue Widget", current_stock="0.000")
        procesada = _upload_invoice(client, auth_headers, mocker)
        invoice_id = procesada.json()["invoice_id"]
        items = procesada.json()["items"]
        client.post(f"/invoices/{invoice_id}/confirm", json={"items": [
            {"invoice_item_id": items[0]["id"], "product_id": product["id"]},
            {"invoice_item_id": items[1]["id"], "skip": True},
        ]}, headers=auth_headers)

        resp = client.get(f"/invoices/{invoice_id}", headers=auth_headers)
        assert all(i["suggested_product_id"] is None for i in resp.json()["items"])
