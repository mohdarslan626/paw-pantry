
from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_does_not_store_plain_text():
    password = "TestPassword123!"

    hashed = hash_password(password)

    assert hashed != password


def test_hash_password_uses_different_salts():
    password = "TestPassword123!"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash


def test_verify_password_accepts_correct_password():
    password = "TestPassword123!"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("TestPassword123!")

    assert verify_password("WrongPassword123!", hashed) is False


def test_create_and_decode_access_token():
    token = create_access_token("test-user-id")

    payload = decode_access_token(token)

    assert payload["sub"] == "test-user-id"
    assert "iat" in payload
    assert "exp" in payload


def test_decode_access_token_rejects_expired_token():
    token = create_access_token(
        "test-user-id",
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_decode_access_token_rejects_tampered_signature():
    token = create_access_token("test-user-id")
    parts = token.split(".")

    parts[2] = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
    tampered_token = ".".join(parts)

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(tampered_token)
