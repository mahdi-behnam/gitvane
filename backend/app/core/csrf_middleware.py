import secrets
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.errors import CSRFError


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/")
        
        # Check CSRF only for POST requests to refresh or logout endpoints
        if request.method == "POST" and path in [
            f"{settings.API_V1_PREFIX}/auth/refresh",
            f"{settings.API_V1_PREFIX}/auth/logout",
        ]:
            csrf_token_header = request.headers.get("X-CSRF-Token")
            csrf_token_cookie = request.cookies.get("csrf_token")

            if not csrf_token_header or not csrf_token_cookie or csrf_token_header != csrf_token_cookie:
                # Return HTTP 403 Forbidden directly to bypass Starlette middleware exception handling issues
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "CSRF token validation failed",
                        "error_type": "CSRFError",
                    },
                )

        response = await call_next(request)

        # On every response, check if the client has a csrf_token cookie.
        # If not, generate a cryptographically secure token and set it.
        if "csrf_token" not in request.cookies:
            token = secrets.token_urlsafe(32)
            secure = settings.ENVIRONMENT != "local"
            response.set_cookie(
                key="csrf_token",
                value=token,
                path="/",
                httponly=False,
                samesite="lax",
                secure=secure,
            )

        return response
