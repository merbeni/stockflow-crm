"""Tests de integración de /auth: alta pública, verificación de correo y login."""
from tests.conftest import _marcar_verificado, signup_organization

ALTA_VALIDA = {
    "organization_name": "Distribuidora del Sur",
    "full_name": "Ana Gómez",
    "email": "ana@test.com",
    "phone": "+54 11 5555-1234",
    "password": "password123",
}


class TestSignup:
    def test_crea_organizacion_y_administrador(self, client):
        resp = client.post("/auth/signup", json=ALTA_VALIDA)
        assert resp.status_code == 201, resp.text
        data = resp.json()

        assert data["organization"]["name"] == "Distribuidora del Sur"
        assert data["organization"]["slug"] == "distribuidora-del-sur"
        assert data["user"]["email"] == "ana@test.com"
        # Solo el alta pública otorga el rol de administrador, y únicamente
        # sobre la organización recién creada.
        assert data["user"]["role"] == "admin"
        assert data["user"]["is_email_verified"] is False
        assert data["email_verification_required"] is True
        # El alta devuelve un mensaje explícito: antes no había ninguna
        # devolución al usuario tras registrarse.
        assert "correo" in data["message"].lower()
        assert "hashed_password" not in data["user"]

    def test_slug_unico_cuando_se_repite_el_nombre(self, client):
        client.post("/auth/signup", json=ALTA_VALIDA)
        segunda = {**ALTA_VALIDA, "email": "otra@test.com"}
        resp = client.post("/auth/signup", json=segunda)
        assert resp.status_code == 201
        assert resp.json()["organization"]["slug"] == "distribuidora-del-sur-2"

    def test_correo_duplicado_da_400(self, client):
        client.post("/auth/signup", json=ALTA_VALIDA)
        resp = client.post("/auth/signup", json=ALTA_VALIDA)
        assert resp.status_code == 400
        assert isinstance(resp.json()["detail"], str)
        assert resp.json()["errors"]["email"]

    def test_correo_invalido_da_422_con_mensaje_legible(self, client):
        resp = client.post("/auth/signup", json={**ALTA_VALIDA, "email": "no-es-mail"})
        assert resp.status_code == 422
        cuerpo = resp.json()
        # El detail tiene que ser un string: cuando era una lista de objetos el
        # frontend se quedaba en blanco al intentar renderizarlo.
        assert isinstance(cuerpo["detail"], str)
        assert "email" in cuerpo["errors"]

    def test_nombre_de_persona_con_numeros_da_422(self, client):
        resp = client.post("/auth/signup", json={**ALTA_VALIDA, "full_name": "Ana 123"})
        assert resp.status_code == 422
        assert "números" in resp.json()["errors"]["full_name"]

    def test_telefono_invalido_da_422(self, client):
        resp = client.post("/auth/signup", json={**ALTA_VALIDA, "phone": "abc"})
        assert resp.status_code == 422
        assert "phone" in resp.json()["errors"]

    def test_contrasena_debil_da_422(self, client):
        resp = client.post("/auth/signup", json={**ALTA_VALIDA, "password": "corta"})
        assert resp.status_code == 422
        assert "password" in resp.json()["errors"]

    def test_falta_la_contrasena_da_422(self, client):
        payload = {k: v for k, v in ALTA_VALIDA.items() if k != "password"}
        resp = client.post("/auth/signup", json=payload)
        assert resp.status_code == 422


class TestVerificacionDeCorreo:
    def _token_de(self, email):
        from tests.conftest import _TestingSession
        from app.models.user import User

        session = _TestingSession()
        try:
            return (
                session.query(User).filter(User.email == email).first()
            ).email_verification_token
        finally:
            session.close()

    def test_verifica_con_un_token_valido(self, client):
        client.post("/auth/signup", json=ALTA_VALIDA)
        token = self._token_de("ana@test.com")

        resp = client.get("/auth/verify-email", params={"token": token})
        assert resp.status_code == 200
        assert "verificado" in resp.json()["message"].lower()

        # Con el correo verificado el login ya funciona.
        login = client.post(
            "/auth/login", json={"email": "ana@test.com", "password": "password123"}
        )
        assert login.status_code == 200

    def test_el_token_es_de_un_solo_uso(self, client):
        client.post("/auth/signup", json=ALTA_VALIDA)
        token = self._token_de("ana@test.com")
        assert client.get("/auth/verify-email", params={"token": token}).status_code == 200
        assert client.get("/auth/verify-email", params={"token": token}).status_code == 400

    def test_token_invalido_da_400(self, client):
        resp = client.get("/auth/verify-email", params={"token": "x" * 40})
        assert resp.status_code == 400
        assert isinstance(resp.json()["detail"], str)

    def test_reenvio_no_revela_si_la_cuenta_existe(self, client):
        client.post("/auth/signup", json=ALTA_VALIDA)
        conocida = client.post("/auth/resend-verification", json={"email": "ana@test.com"})
        desconocida = client.post(
            "/auth/resend-verification", json={"email": "nadie@test.com"}
        )
        assert conocida.status_code == desconocida.status_code == 200
        assert conocida.json() == desconocida.json()

    def test_el_correo_no_distingue_mayusculas(self, client):
        """
        "Ana@test.com" y "ana@test.com" son la misma casilla. Sin normalizar,
        se creaban dos cuentas distintas y quien se registraba con mayúsculas
        no podía volver a entrar escribiéndolo en minúsculas.
        """
        alta = client.post("/auth/signup", json={**ALTA_VALIDA, "email": "Ana@Test.com"})
        assert alta.status_code == 201
        assert alta.json()["user"]["email"] == "ana@test.com"

        duplicada = client.post(
            "/auth/signup",
            json={**ALTA_VALIDA, "organization_name": "Otra", "email": "ANA@TEST.COM"},
        )
        assert duplicada.status_code == 400, "no debería permitir una segunda cuenta"

        _marcar_verificado("ana@test.com")
        login = client.post(
            "/auth/login", json={"email": "ANA@test.COM", "password": "password123"}
        )
        assert login.status_code == 200, "debe poder entrar escribiéndolo distinto"

    def test_la_bienvenida_se_envia_al_verificar_y_no_al_registrarse(self, client, mocker):
        """
        Al registrarse llegaban dos correos a la vez: el de verificación y uno de
        bienvenida que invitaba a iniciar sesión. Era contradictorio, porque hasta
        confirmar la dirección el login está bloqueado.
        """
        bienvenida = mocker.patch("app.routers.auth.send_welcome_email")

        client.post("/auth/signup", json=ALTA_VALIDA)
        assert bienvenida.call_count == 0, "no debe enviarse al registrarse"

        token = self._token_de("ana@test.com")
        assert client.get("/auth/verify-email", params={"token": token}).status_code == 200
        bienvenida.assert_called_once_with(user_email="ana@test.com")


class TestLogin:
    def test_login_correcto_devuelve_token(self, client):
        client.post("/auth/signup", json=ALTA_VALIDA)
        _marcar_verificado("ana@test.com")
        resp = client.post(
            "/auth/login", json={"email": "ana@test.com", "password": "password123"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_sin_verificar_el_correo_da_403(self, client):
        client.post("/auth/signup", json=ALTA_VALIDA)
        resp = client.post(
            "/auth/login", json={"email": "ana@test.com", "password": "password123"}
        )
        assert resp.status_code == 403
        assert "verificaste" in resp.json()["detail"].lower()

    def test_contrasena_incorrecta_da_401(self, client):
        client.post("/auth/signup", json=ALTA_VALIDA)
        _marcar_verificado("ana@test.com")
        resp = client.post(
            "/auth/login", json={"email": "ana@test.com", "password": "otracosa9"}
        )
        assert resp.status_code == 401

    def test_correo_desconocido_da_401(self, client):
        resp = client.post(
            "/auth/login", json={"email": "nadie@test.com", "password": "password123"}
        )
        assert resp.status_code == 401

    def test_usuario_desactivado_no_puede_entrar(self, client, auth_headers, operator_token):
        # El administrador desactiva al operador y este pierde el acceso.
        usuarios = client.get("/users", headers=auth_headers).json()
        operador = next(u for u in usuarios if u["role"] == "operator")
        client.put(f"/users/{operador['id']}", json={"is_active": False}, headers=auth_headers)

        resp = client.post(
            "/auth/login", json={"email": "operator@test.com", "password": "password123"}
        )
        assert resp.status_code == 403
        assert "desactivada" in resp.json()["detail"].lower()


class TestMe:
    def test_devuelve_el_usuario_actual(self, client, auth_headers):
        resp = client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "admin@test.com"
        assert data["role"] == "admin"
        assert data["organization_id"]

    def test_sin_token_da_401(self, client):
        assert client.get("/auth/me").status_code == 401

    def test_token_invalido_da_401(self, client):
        resp = client.get("/auth/me", headers={"Authorization": "Bearer no-sirve"})
        assert resp.status_code == 401

    def test_devuelve_la_organizacion(self, client, auth_headers):
        resp = client.get("/auth/my-organization", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Organización de prueba"


class TestRegistroInterno:
    def test_register_publico_ya_no_existe(self, client):
        # Antes cualquiera podía llamar a /auth/register y pedir rol admin.
        resp = client.post(
            "/auth/register",
            json={"email": "intruso@test.com", "password": "password123", "role": "admin"},
        )
        assert resp.status_code == 404

    def test_un_operador_no_puede_crear_usuarios(self, client, operator_headers):
        resp = client.post(
            "/users",
            json={
                "email": "nuevo@test.com",
                "password": "password123",
                "full_name": "Nuevo Usuario",
                "role": "admin",
            },
            headers=operator_headers,
        )
        assert resp.status_code == 403

    def test_el_admin_crea_usuarios_en_su_organizacion(self, client, auth_headers):
        resp = client.post(
            "/users",
            json={
                "email": "nuevo@test.com",
                "password": "password123",
                "full_name": "Nuevo Usuario",
                "role": "operator",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        creado = resp.json()
        yo = client.get("/auth/me", headers=auth_headers).json()
        assert creado["organization_id"] == yo["organization_id"]
        assert creado["is_email_verified"] is False

    def test_no_se_puede_dejar_la_organizacion_sin_administradores(self, client, auth_headers):
        yo = client.get("/auth/me", headers=auth_headers).json()
        resp = client.put(
            f"/users/{yo['id']}", json={"role": "operator"}, headers=auth_headers
        )
        assert resp.status_code == 400
        assert "administrador" in resp.json()["detail"].lower()

    def test_no_se_puede_eliminar_la_propia_cuenta(self, client, auth_headers):
        yo = client.get("/auth/me", headers=auth_headers).json()
        resp = client.delete(f"/users/{yo['id']}", headers=auth_headers)
        assert resp.status_code == 400

    def test_no_se_ven_usuarios_de_otra_organizacion(self, client, auth_headers, other_org_headers):
        mios = client.get("/users", headers=auth_headers).json()
        otros = client.get("/users", headers=other_org_headers).json()
        correos_mios = {u["email"] for u in mios}
        correos_otros = {u["email"] for u in otros}
        assert correos_mios.isdisjoint(correos_otros)

    def test_no_se_puede_editar_un_usuario_de_otra_organizacion(
        self, client, auth_headers, other_org_headers
    ):
        ajeno = client.get("/users", headers=other_org_headers).json()[0]
        resp = client.put(
            f"/users/{ajeno['id']}", json={"is_active": False}, headers=auth_headers
        )
        # 404 y no 403: confirmar que existe ya sería filtrar datos de otro cliente.
        assert resp.status_code == 404


def test_signup_organization_helper(client):
    """El helper de conftest deja una sesión utilizable de punta a punta."""
    token = signup_organization(client, email="helper@test.com")
    resp = client.get("/auth/me", headers={"Authorization": "Bearer " + token})
    assert resp.status_code == 200
