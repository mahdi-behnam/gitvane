from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import logger


class RepoLensError(Exception):
    """Base exception for all RepoLens errors"""

    message: str = "An unexpected error occurred"

    def __init__(self, message: str | None = None) -> None:
        if message:
            self.message = message
        super().__init__(self.message)


class RepositoryNotFoundError(RepoLensError):
    message = "Repository not found"


class InvalidPathError(RepoLensError):
    message = "Invalid or insecure path path traversal detected"


class EmbeddingDimensionMismatchError(RepoLensError):
    message = "Embedding dimensions mismatch"


class ParserError(RepoLensError):
    message = "Failed to parse source file"


class GitOperationError(RepoLensError):
    message = "Git operation failed"


class PrivateRepositoryNotSupportedError(RepoLensError):
    message = "Private repositories are not yet supported. Please use a public repository URL."


class AuthenticationError(RepoLensError):
    message = "Invalid or expired credentials"


class AuthorizationError(RepoLensError):
    message = "Access denied: insufficient permissions"


class CSRFError(RepoLensError):
    message = "CSRF token validation failed"


def setup_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RepoLensError)
    async def repolens_exception_handler(
        request: Request, exc: RepoLensError
    ) -> JSONResponse:
        logger.error(
            f"RepoLens error occurred during request {request.url.path}: {exc.message}",
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
