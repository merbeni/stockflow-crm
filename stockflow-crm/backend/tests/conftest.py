"""
Test configuration.

Sets env vars and patches PostgreSQL-specific types BEFORE any app module is
imported so that tests run against an in-memory SQLite database without needing
a real PostgreSQL instance.
"""
import os

# ── env vars must come first ──────────────────────────────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("GOOGLE_API_KEY", "test-api-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-chars!!")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")

# ── patch JSONB → JSON so SQLite can create the schema ───────────────────────
from sqlalchemy.types import JSON  # noqa: E402
import sqlalchemy.dialects.postgresql as _pg

_pg.JSONB = JSON  # type: ignore[attr-defined]

# ── now safe to import app ────────────────────────────────────────────────────
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from sqlalchemy import event  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

# ── test database ─────────────────────────────────────────────────────────────
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


# Enable FK enforcement so IntegrityError is raised on constrained deletes
@event.listens_for(_engine, "connect")
def _set_sqlite_fk_pragma(dbapi_connection, _):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
_TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

Base.metadata.create_all(bind=_engine)


def _override_get_db():
    db = _TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_db():
    """Wipe and recreate all tables before every test."""
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)
    yield


@pytest.fixture
def db():
    session = _TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ── auth helpers ──────────────────────────────────────────────────────────────

from app.models.user import User  # noqa: E402


def _marcar_verificado(email: str) -> None:
    """
    Marca el correo como verificado.

    El alta deja al usuario sin verificar y el login lo rechaza hasta que
    confirme su dirección; en los tests no hay bandeja de entrada, así que se
    confirma directamente contra la base.
    """
    session = _TestingSession()
    try:
        user = session.query(User).filter(User.email == email).first()
        assert user is not None, f"No se creó el usuario {email}"
        user.is_email_verified = True
        session.commit()
    finally:
        session.close()


def _login(client, email: str, password: str) -> str:
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def signup_organization(
    client,
    *,
    email: str = "admin@test.com",
    password: str = "password123",
    organization_name: str = "Organización de prueba",
    full_name: str = "Ana Gómez",
    phone: str = "+54 11 5555-1234",
) -> str:
    """Da de alta una organización con su administrador y devuelve el token."""
    resp = client.post(
        "/auth/signup",
        json={
            "organization_name": organization_name,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "password": password,
        },
    )
    assert resp.status_code == 201, resp.text
    _marcar_verificado(email)
    return _login(client, email, password)


@pytest.fixture
def admin_token(client):
    return signup_organization(client)


@pytest.fixture
def operator_token(client, auth_headers):
    """Operador dado de alta por el administrador, dentro de su misma organización."""
    email = "operator@test.com"
    resp = client.post(
        "/users",
        json={
            "email": email,
            "password": "password123",
            "full_name": "Beto Pérez",
            "role": "operator",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    _marcar_verificado(email)
    return _login(client, email, "password123")


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ── reusable entity factories ─────────────────────────────────────────────────

@pytest.fixture
def operator_headers(operator_token):
    return {"Authorization": "Bearer " + operator_token}


@pytest.fixture
def other_org_headers(client):
    """Administrador de otra organización, para verificar el aislamiento de datos."""
    token = signup_organization(
        client,
        email="otra@test.com",
        organization_name="Otra empresa",
        full_name="Carla Ruiz",
    )
    return {"Authorization": "Bearer " + token}


@pytest.fixture
def make_product(client, auth_headers):
    def _create(**overrides):
        payload = {
            "sku": "SKU-001",
            "name": "Test Product",
            "price": "10.00",
            "current_stock": "50.000",
            "minimum_stock": "5.000",
        }
        payload.update(overrides)
        resp = client.post("/products", json=payload, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        return resp.json()
    return _create


@pytest.fixture
def make_supplier(client, auth_headers):
    def _create(**overrides):
        payload = {
            "name": "Test Supplier",
            "contact_name": "Jane Doe",
            "email": "supplier@test.com",
            "phone": "555-0001",
        }
        payload.update(overrides)
        resp = client.post("/suppliers", json=payload, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        return resp.json()
    return _create


@pytest.fixture
def make_customer(client, auth_headers):
    def _create(**overrides):
        payload = {
            "name": "Test Customer",
            "email": "customer@test.com",
            "phone": "555-0002",
        }
        payload.update(overrides)
        resp = client.post("/customers", json=payload, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        return resp.json()
    return _create
