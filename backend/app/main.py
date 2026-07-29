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
from app.core.csrf_middleware import CSRFMiddleware
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

        # Warm up embedding model to avoid cold-start latency for the first user request
        if settings.EMBEDDING_PROVIDER.lower() == "local":
            logger.info("Warming up local embedding model...")
            try:
                from app.embeddings.service import EmbeddingService
                service = EmbeddingService()
                service.provider._load_model()
                logger.info("Local embedding model warmed up successfully.")
            except Exception as e:
                logger.error(f"Failed to warm up local embedding model: {e}")
        # Recovery: Resume indexing for any repositories that were interrupted by server restart
        try:
            import asyncio
            from sqlalchemy import select
            from app.db.session import SessionLocal
            from app.db.models import Repository
            from app.services.git_service import GitService
            from app.services.indexing_service import IndexingService

            async def recover_indexing_jobs():
                async with SessionLocal() as async_db:
                    result = await async_db.execute(
                        select(Repository).where(Repository.status == "indexing")
                    )
                    interrupted_repos = result.scalars().all()
                    for repo in interrupted_repos:
                        logger.info(f"Recovering interrupted indexing for repository ID={repo.id} ({repo.name})...")
                        try:
                            git_service = GitService()
                            indexing_service = IndexingService(git_service=git_service)
                            await indexing_service.index_repository(
                                db=async_db,
                                repository_id=repo.id,
                                ref=repo.current_ref,
                            )
                        except Exception as recovery_err:
                            logger.error(f"Failed recovery indexing for repo {repo.id}: {recovery_err}")

            asyncio.create_task(recover_indexing_jobs())
        except Exception as recovery_setup_err:
            logger.error(f"Failed setting up indexing recovery task: {recovery_setup_err}")
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

app.add_middleware(CSRFMiddleware)

# Set up error exception handlers
setup_error_handlers(app)

# Include routing
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
