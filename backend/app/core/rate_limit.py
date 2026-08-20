import hashlib
import logging
from typing import Optional

import jwt
from fastapi import Request
from slowapi import Limiter

from app.core.config import settings

logger = logging.getLogger("gitvane")


def get_client_ip(request: Request) -> str:
    """Extract client IP address from proxy headers or direct client connection."""
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip()

    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        ips = [ip.strip() for ip in x_forwarded_for.split(",") if ip.strip()]
        if ips:
            return ips[0]

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


def get_rate_limit_key(request: Request) -> str:
    """Identity-aware rate limiting key extractor.

    Priority:
    1. Authenticated User (via JWT Bearer sub or request.state.user)
    2. API Key / MCP Client header (X-API-Key or X-MCP-Client)
    3. Client IP (via X-Real-IP, X-Forwarded-For, or direct remote addr)
    """
    # 1. Check authenticated user on request.state if set
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"

    # 2. Check Authorization Bearer token in headers
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_signature": True, "verify_exp": True},
            )
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except Exception:
            # Fallback to hashed token if payload is malformed / unverified
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
            return f"token:{token_hash}"

    # 3. Check for API Key / MCP client headers
    api_key = request.headers.get("X-API-Key") or request.headers.get("X-MCP-Client")
    if api_key:
        key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]
        return f"mcp:{key_hash}"

    # 4. Fallback to client IP address
    return f"ip:{get_client_ip(request)}"


def create_limiter() -> Limiter:
    """Create and configure SlowAPI Limiter instance with Redis or in-memory storage."""
    storage_uri: Optional[str] = settings.RATE_LIMIT_STORAGE_URI

    if not storage_uri:
        if settings.ENVIRONMENT.lower() in ("test", "testing"):
            storage_uri = "memory://"
        else:
            storage_uri = settings.REDIS_URL

    default_limits = (
        [settings.RATE_LIMIT_DEFAULT]
        if settings.RATE_LIMIT_DEFAULT and settings.RATE_LIMIT_DEFAULT.strip()
        else None
    )

    try:
        limiter = Limiter(
            key_func=get_rate_limit_key,
            default_limits=default_limits,
            storage_uri=storage_uri,
            strategy=settings.RATE_LIMIT_STRATEGY,
            enabled=settings.RATE_LIMIT_ENABLED,
            headers_enabled=False,
            swallow_errors=True,  # Fail open if storage is unreachable
        )
        logger.info(f"Rate limiter initialized with storage: {storage_uri}")
        return limiter
    except Exception as e:
        logger.warning(
            f"Failed to initialize rate limiter with storage {storage_uri} ({e}). "
            "Falling back to in-memory storage."
        )
        return Limiter(
            key_func=get_rate_limit_key,
            default_limits=default_limits,
            storage_uri="memory://",
            strategy=settings.RATE_LIMIT_STRATEGY,
            enabled=settings.RATE_LIMIT_ENABLED,
            headers_enabled=False,
            swallow_errors=True,
        )


limiter = create_limiter()
