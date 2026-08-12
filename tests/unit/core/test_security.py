import time

import jwt
import pytest

from app.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_hash_and_verify_password_roundtrip():
    hashed = hash_password("s3cret!")

    assert hashed != "s3cret!"
    assert verify_password("s3cret!", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    token = create_access_token(user_id=42)

    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert payload["type"] == "access"


def test_decode_expired_token_raises():
    expired_payload = {"sub": "1", "type": "access", "exp": int(time.time()) - 10}
    expired_token = jwt.encode(expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token)


def test_generate_refresh_token_returns_raw_and_matching_hash():
    raw, token_hash = generate_refresh_token()

    assert raw != token_hash
    assert hash_refresh_token(raw) == token_hash
