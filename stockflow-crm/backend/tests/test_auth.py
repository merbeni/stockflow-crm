"""Integration tests for /auth routes."""
import pytest


class TestRegister:
    def test_register_operator_success(self, client):
        resp = client.post("/auth/register", json={
            "email": "new@test.com",
            "password": "password123",
            "role": "operator",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@test.com"
        assert data["role"] == "operator"
        assert "id" in data
        assert "hashed_password" not in data

    def test_register_admin_role(self, client):
        resp = client.post("/auth/register", json={
            "email": "admin@test.com",
            "password": "password123",
            "role": "admin",
        })
        assert resp.status_code == 201
        assert resp.json()["role"] == "admin"

    def test_register_default_role_is_operator(self, client):
        resp = client.post("/auth/register", json={
            "email": "noRole@test.com",
            "password": "password123",
        })
        assert resp.status_code == 201
        assert resp.json()["role"] == "operator"

    def test_register_duplicate_email_returns_400(self, client):
        payload = {"email": "dup@test.com", "password": "password123"}
        client.post("/auth/register", json=payload)
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    def test_register_invalid_email_returns_422(self, client):
        resp = client.post("/auth/register", json={
            "email": "not-an-email",
            "password": "password123",
        })
        assert resp.status_code == 422

    def test_register_missing_password_returns_422(self, client):
        resp = client.post("/auth/register", json={"email": "user@test.com"})
        assert resp.status_code == 422


class TestLogin:
    def test_login_success_returns_token(self, client):
        client.post("/auth/register", json={
            "email": "user@test.com",
            "password": "password123",
        })
        resp = client.post("/auth/login", json={
            "email": "user@test.com",
            "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self, client):
        client.post("/auth/register", json={
            "email": "user@test.com",
            "password": "password123",
        })
        resp = client.post("/auth/login", json={
            "email": "user@test.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_unknown_email_returns_401(self, client):
        resp = client.post("/auth/login", json={
            "email": "nobody@test.com",
            "password": "password123",
        })
        assert resp.status_code == 401


class TestMe:
    def test_me_returns_current_user(self, client, auth_headers):
        resp = client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "admin@test.com"

    def test_me_without_token_returns_401(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token_returns_401(self, client):
        resp = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401
