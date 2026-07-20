from datetime import timedelta
import pytest
from app.core.errors import AuthenticationError
from app.core.security_utils import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_secure_token,
    encrypt_pat,
    decrypt_pat,
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
    # Create an expired token by setting delta to negative value
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
