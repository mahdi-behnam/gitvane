from datetime import timedelta

import pytest

from app.core.errors import AuthenticationError
from app.core.security_utils import (
    create_access_token,
    create_password_reset_token,
    decode_access_token,
    decrypt_pat,
    encrypt_pat,
    generate_api_key,
    generate_secure_token,
    hash_api_key,
    hash_password,
    verify_api_key,
    verify_password,
    verify_password_reset_token,
)


def test_password_hashing() -> None:
    password = "secret_password_123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False
    assert verify_password(password, "invalid_hash") is False


def test_jwt_access_token() -> None:
    subject = "user123"
    token = create_access_token(subject, expires_delta=timedelta(minutes=5))
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload["sub"] == subject
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_expired_token() -> None:
    subject = "user456"
    token = create_access_token(subject, expires_delta=timedelta(minutes=-5))

    with pytest.raises(AuthenticationError):
        decode_access_token(token)


def test_jwt_invalid_token() -> None:
    with pytest.raises(AuthenticationError):
        decode_access_token("invalid.jwt.token")


def test_generate_secure_token() -> None:
    token1 = generate_secure_token()
    token2 = generate_secure_token()
    assert len(token1) > 0
    assert token1 != token2


def test_pat_encryption_decryption() -> None:
    pat = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    encrypted = encrypt_pat(pat)
    assert encrypted != pat

    decrypted = decrypt_pat(encrypted)
    assert decrypted == pat


def test_password_reset_token() -> None:
    email = "user@example.com"
    token = create_password_reset_token(email)
    assert isinstance(token, str)

    verified_email = verify_password_reset_token(token)
    assert verified_email == email


def test_api_key_generation() -> None:
    raw_key, key_prefix, hashed_key = generate_api_key()

    # Prefix and structure assertions
    assert raw_key.startswith("gv_live_")
    assert key_prefix == raw_key[:12]
    assert len(key_prefix) == 12

    # Hash correctness
    expected_hash = hash_api_key(raw_key)
    assert hashed_key == expected_hash

    # Verification assertions
    assert verify_api_key(raw_key, hashed_key) is True
    assert verify_api_key("wrong_key", hashed_key) is False
    assert verify_api_key(raw_key, "invalid_hash_string") is False


def test_api_key_uniqueness() -> None:
    key1, prefix1, hash1 = generate_api_key()
    key2, prefix2, hash2 = generate_api_key()

    assert key1 != key2
    assert prefix1 != prefix2
    assert hash1 != hash2


def test_hash_api_key_deterministic() -> None:
    key = "gv_live_test_deterministic_key_12345"
    hash1 = hash_api_key(key)
    hash2 = hash_api_key(key)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex digest length
