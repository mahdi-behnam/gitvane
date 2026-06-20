from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import setup_error_handlers
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Initialize logging
    setup_logging()
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
