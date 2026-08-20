from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.logging import logger


class GitVaneError(Exception):
    """Base exception for all GitVane errors"""

    message: str = "An unexpected error occurred"

    def __init__(self, message: str | None = None) -> None:
        if message:
            self.message = message
        super().__init__(self.message)


class RepositoryNotFoundError(GitVaneError):
    message = "Repository not found"


class InvalidPathError(GitVaneError):
    message = "Invalid or insecure path path traversal detected"


class EmbeddingDimensionMismatchError(GitVaneError):
    message = "Embedding dimensions mismatch"


class ParserError(GitVaneError):
    message = "Failed to parse source file"


class GitOperationError(GitVaneError):
    message = "Git operation failed"


class PrivateRepositoryNotSupportedError(GitVaneError):
    message = "Private repositories are not yet supported. Please use a public repository URL."


class SecurityValidationError(GitVaneError):
    message = "Security validation failed"


class SSRFValidationError(SecurityValidationError):
    message = "Target URL or IP address failed SSRF safety checks"


class ResourceLimitExceededError(SecurityValidationError):
    message = "Repository ingestion resource limit exceeded"


class AuthenticationError(GitVaneError):
    message = "Invalid or expired credentials"


class AuthorizationError(GitVaneError):
    message = "Access denied: insufficient permissions"


class CSRFError(GitVaneError):
    message = "CSRF token validation failed"


def setup_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exceeded_handler(
        request: Request, exc: RateLimitExceeded
    ) -> JSONResponse:
        logger.warning(
            f"Rate limit exceeded during request {request.url.path}: {exc.detail}"
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": f"Rate limit exceeded: {exc.detail}. Please try again later.",
                "error_type": "RateLimitExceeded",
            },
            headers={"Retry-After": "60"},
        )

    @app.exception_handler(GitVaneError)
    async def gitvane_exception_handler(
        request: Request, exc: GitVaneError
    ) -> JSONResponse:
        logger.error(
            f"GitVane error occurred during request {request.url.path}: {exc.message}",
            exc_info=True,
        )
        status_code = status.HTTP_400_BAD_REQUEST
        if isinstance(exc, AuthenticationError):
            status_code = status.HTTP_401_UNAUTHORIZED
        elif isinstance(exc, (AuthorizationError, CSRFError)):
            status_code = status.HTTP_403_FORBIDDEN

        return JSONResponse(
            status_code=status_code,
            content={"detail": exc.message, "error_type": exc.__class__.__name__},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            f"Unhandled exception during request {request.url.path}: {str(exc)}",
            exc_info=True,
        )
        # Avoid exposing SQL errors or internal library details to the user
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred.",
                "error_type": "InternalServerError",
            },
        )
