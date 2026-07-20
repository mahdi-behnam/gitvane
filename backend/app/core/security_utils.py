import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.errors import AuthenticationError


def hash_password(plain_password: str) -> str:
    """
    Hashes plain password using bcrypt and returns the string.
    Converts strings to bytes for bcrypt operation, and decodes the resulting hash back to string.
    """
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies plain password matches the hashed password.
    Handles string/byte conversions safely and returns a boolean.
    """
    try:
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(
    subject: str | int, expires_delta: timedelta | None = None
) -> str:
    """
    Encodes a JWT with sub, exp, and iat claims using settings.JWT_SECRET_KEY
    and algorithm settings.JWT_ALGORITHM.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
    }
    encoded = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    if isinstance(encoded, bytes):
        return encoded.decode("utf-8")
    return encoded


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decodes access token, validates expiration, and returns payload.
    Raises AuthenticationError if expired or invalid.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except (jwt.PyJWTError, ValueError) as e:
        raise AuthenticationError("Invalid or expired credentials") from e


def generate_secure_token() -> str:
    """
    Returns a secure random token using secrets.token_urlsafe(32).
    """
    return secrets.token_urlsafe(32)


def encrypt_pat(pat: str) -> str:
    """
    Encrypts plain PAT using Fernet and settings.ENCRYPTION_KEY.
    """
    fernet = Fernet(settings.ENCRYPTION_KEY.encode("utf-8"))
    encrypted_bytes = fernet.encrypt(pat.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_pat(encrypted_pat: str) -> str:
    """
    Decrypts encrypted PAT and returns plain token.
    """
    fernet = Fernet(settings.ENCRYPTION_KEY.encode("utf-8"))
    decrypted_bytes = fernet.decrypt(encrypted_pat.encode("utf-8"))
    return decrypted_bytes.decode("utf-8")
