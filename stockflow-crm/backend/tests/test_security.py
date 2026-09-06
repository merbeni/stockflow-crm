"""Unit tests for core/security.py — password hashing and JWT."""
from jose import jwt, JWTError
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("mysecret")
        assert hashed != "mysecret"

    def test_verify_correct_password(self):
        hashed = hash_password("mysecret")
        assert verify_password("mysecret", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("mysecret")
        assert verify_password("wrongpassword", hashed) is False

    def test_two_hashes_of_same_password_differ(self):
        h1 = hash_password("mysecret")
        h2 = hash_password("mysecret")
        assert h1 != h2  # bcrypt salts are random


class TestJWT:
    def test_create_and_decode_token(self):
        token = create_access_token("user@example.com")
        subject = decode_token(token)
        assert subject == "user@example.com"

    def test_token_contains_correct_claims(self):
        token = create_access_token("user@example.com")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "user@example.com"
        assert "exp" in payload

    def test_tampered_token_raises(self):
        token = create_access_token("user@example.com")
        tampered = token[:-4] + "XXXX"
        with pytest.raises(JWTError):
            decode_token(tampered)

    def test_token_with_wrong_secret_raises(self):
        token = jwt.encode({"sub": "user@example.com"}, "wrong-secret", algorithm="HS256")
        with pytest.raises(JWTError):
            decode_token(token)


class TestCorsEnErroresNoControlados:
    """
    Un error inesperado del servidor tiene que llegar legible al navegador.

    En Starlette el manejador genérico de ``Exception`` corre en
    ``ServerErrorMiddleware``, que está por fuera de ``CORSMiddleware``: su
    respuesta salía sin ``Allow-Origin``, el navegador la bloqueaba y el cliente
    —al no ver ninguna respuesta— le decía al usuario "No se pudo conectar con
    el servidor". Un error del servidor quedaba disfrazado de problema de red
    del usuario, que es el diagnóstico contrario y manda a revisar donde no es.
    """

    def _romper(self, mocker, headers):
        """
        Provoca un error no controlado y devuelve la respuesta HTTP real.

        Se usa un TestClient propio con ``raise_server_exceptions=False``: el
        cliente por defecto vuelve a lanzar la excepción en lugar de devolver el
        500, y acá lo que se quiere inspeccionar son justamente las cabeceras de
        esa respuesta, que es lo que llega al navegador.
        """
        from fastapi.testclient import TestClient
        from app.main import app

        mocker.patch(
            "app.routers.products.list_products",
            side_effect=RuntimeError("fallo inesperado"),
        )
        with TestClient(app, raise_server_exceptions=False) as c:
            return c.get("/products", headers=headers)

    def test_el_500_conserva_las_cabeceras_cors(self, client, auth_headers, mocker):
        origen = "http://localhost:5173"
        resp = self._romper(mocker, {**auth_headers, "Origin": origen})

        assert resp.status_code == 500
        assert resp.headers.get("access-control-allow-origin") == origen, (
            "sin esta cabecera el navegador no puede leer el error y lo reporta "
            "como falta de conexión"
        )
        # Y el cuerpo sigue siendo el formato uniforme, sin filtrar la traza.
        assert isinstance(resp.json()["detail"], str)
        assert "RuntimeError" not in resp.json()["detail"]

    def test_no_refleja_un_origen_no_permitido(self, client, auth_headers, mocker):
        resp = self._romper(
            mocker, {**auth_headers, "Origin": "https://sitio-malicioso.com"}
        )

        assert resp.status_code == 500
        assert resp.headers.get("access-control-allow-origin") is None, (
            "reflejar cualquier origen abriría un agujero que el resto de la "
            "aplicación no tiene"
        )
