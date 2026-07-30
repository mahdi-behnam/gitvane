import os
from typing import Any, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            ),
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "RepoLens"
    ENVIRONMENT: str = "local"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+asyncpg://repolens:repolens@localhost:5432/repolens"
    SYNC_DATABASE_URL: str = (
        "postgresql+psycopg://repolens:repolens@localhost:5432/repolens"
    )

    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30

    REDIS_URL: str = "redis://localhost:6379/0"

    REPOLENS_WORKSPACE: str = "./workspace/repos"
    MAX_INDEX_FILE_SIZE_KB: int = 512
    MAX_COMMITS_TO_MINE: int = 500
    MAX_EVAL_COMMITS: int = 100

    EMBEDDING_PROVIDER: str = "local"
    LOCAL_EMBEDDING_MODEL: str = "jinaai/jina-embeddings-v2-base-code"
    LOCAL_EMBEDDING_REVISION: Optional[str] = "516f4baf13dec4ddddda8631e019b5737c8bc250"
    EMBEDDING_DIM: int = 768
    EMBEDDING_BATCH_SIZE: int = 16
    USE_CUDA_IF_AVAILABLE: bool = True

    NVIDIA_API_KEY: Optional[str] = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_LLM_MODEL: str = "nvidia/llama-3.1-nemotron-nano-8b-v1"
    NVIDIA_EMBEDDING_MODEL: str = "nvidia/nv-embedcode-7b-v1"

    ENABLE_LLM_EXPLANATIONS: bool = True
    LLM_TIMEOUT_SECONDS: int = 30

    IMPACT_DEPENDENCY_WEIGHT: float = 0.35
    IMPACT_SEMANTIC_WEIGHT: float = 0.25
    IMPACT_COCHANGE_WEIGHT: float = 0.20
    IMPACT_TEST_WEIGHT: float = 0.10
    IMPACT_RISK_WEIGHT: float = 0.10

    FRONTEND_URL: str = "http://localhost:3000/auth/callback"
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 90
    ENCRYPTION_KEY: str = ""
    GOOGLE_CLIENT_ID: Optional[str] = ""
    GOOGLE_CLIENT_SECRET: Optional[str] = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/oauth2/callback/google"

    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: str = "noreply@repolens.dev" 

    def model_post_init(self, __context: Any) -> None:
        if not self.JWT_SECRET_KEY:
            if self.ENVIRONMENT.lower() not in ("local", "test", "testing"):
                raise ValueError(
                    "JWT_SECRET_KEY environment variable is required in non-local environments"
                )
            import logging
            import secrets
            self.JWT_SECRET_KEY = secrets.token_hex(32)
            logging.getLogger("repolens").warning(
                "JWT_SECRET_KEY is not set in environment or env file. "
                "Generating a random ephemeral secret key. This is not suitable for horizontal scaling."
            )
        if not self.ENCRYPTION_KEY:
            import logging

            from cryptography.fernet import Fernet
            self.ENCRYPTION_KEY = Fernet.generate_key().decode()
            logging.getLogger("repolens").warning(
                "ENCRYPTION_KEY is not set in environment or env file. "
                "Generating a random ephemeral Fernet key. This is not suitable for horizontal scaling."
            )


settings = Settings()
