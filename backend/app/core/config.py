import os
from typing import Optional

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


settings = Settings()
