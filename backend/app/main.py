from contextlib import asynccontextmanager
import logging
import os
import subprocess
import sys
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import setup_error_handlers
from app.core.logging import setup_logging

logger = logging.getLogger("repolens")

# Locate backend directory containing alembic.ini relative to this file
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Initialize logging
    setup_logging()

    # Run database migrations
    if "pytest" not in sys.modules:
        logger.info("Running database migrations...")
        try:
            # We run 'alembic upgrade head' as a subprocess inside the virtual env
            subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=backend_dir,
                check=True,
            )
            logger.info("Database migrations applied successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to run database migrations: {e}")
            # Raise exception to prevent application from booting with out-of-sync schema
            raise RuntimeError("Migration failure during startup") from e
    else:
        logger.info("Skipping database migrations in test environment.")

    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Intelligent Predictive Code Change Analysis Engine",
    version="0.1.0",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

# Apply secure CORS rules. No wildcard origins.
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Set up error exception handlers
setup_error_handlers(app)

# Include routing
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
