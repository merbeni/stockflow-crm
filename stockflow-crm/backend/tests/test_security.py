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
