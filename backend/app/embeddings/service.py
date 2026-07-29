from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import EmbeddingDimensionMismatchError
from app.db.models import CodeChunk, CodeEmbedding
from app.embeddings.base import EmbeddingProvider
from app.embeddings.local_provider import LocalSentenceTransformerProvider
from app.embeddings.nim_provider import NimEmbeddingProvider


class EmbeddingService:
    """Coordinate embedding providers and persistence checks."""

    def __init__(self, provider: EmbeddingProvider | None = None) -> None:
        self._provider = provider

    @property
    def provider(self) -> EmbeddingProvider:
        if self._provider is None:
            self._provider = self.build_provider()
        return self._provider

    def build_provider(self) -> EmbeddingProvider:
        configured_provider = settings.EMBEDDING_PROVIDER.lower()
        if configured_provider == "nim":
            return NimEmbeddingProvider(
                api_key=settings.NVIDIA_API_KEY or "",
                base_url=settings.NVIDIA_BASE_URL,
                model_name=settings.NVIDIA_EMBEDDING_MODEL,
                dimensions=settings.EMBEDDING_DIM,
                timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
            )
        if configured_provider != "local":
            raise ValueError(
                "Unsupported EMBEDDING_PROVIDER. Expected 'local' or 'nim'."
            )
        return LocalSentenceTransformerProvider(
            model_name=settings.LOCAL_EMBEDDING_MODEL,
            dimensions=settings.EMBEDDING_DIM,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            use_cuda_if_available=settings.USE_CUDA_IF_AVAILABLE,
            revision=settings.LOCAL_EMBEDDING_REVISION,
        )

    async def embed_passages(self, texts: list[str]) -> list[list[float]]:
        embeddings = await self.provider.embed_passages(texts)
        self.validate_embeddings(embeddings)
        return embeddings

    async def embed_query(self, text: str) -> list[float]:
        embedding = await self.provider.embed_query(text)
        self.validate_embedding(embedding)
        return embedding

    def validate_embeddings(self, embeddings: Sequence[Sequence[float]]) -> None:
        for embedding in embeddings:
            self.validate_embedding(embedding)

    def validate_embedding(self, embedding: Sequence[float]) -> None:
        if len(embedding) != settings.EMBEDDING_DIM:
            raise EmbeddingDimensionMismatchError(
                "Embedding dimension mismatch: provider returned "
                f"{len(embedding)} dimensions, but EMBEDDING_DIM is "
                f"{settings.EMBEDDING_DIM}. Change EMBEDDING_DIM, regenerate "
                "migrations if the pgvector column dimension changes, and reindex."
            )

    async def needs_embedding(self, db: AsyncSession, chunk: CodeChunk) -> bool:
        existing = await self._get_existing_embedding(db, chunk)
        if existing is None:
            return True
        return (
            existing.provider != settings.EMBEDDING_PROVIDER
            or existing.model != self.provider.model_name
            or existing.dimensions != settings.EMBEDDING_DIM
        )

    async def save_embeddings_for_chunks(
        self,
        db: AsyncSession,
        chunks: Sequence[CodeChunk],
        progress_callback: object = None,
    ) -> int:
        chunks_to_embed = [
            chunk for chunk in chunks if await self.needs_embedding(db, chunk)
        ]
        if not chunks_to_embed:
            return 0

        total_to_embed = len(chunks_to_embed)
        batch_size = max(1, settings.EMBEDDING_BATCH_SIZE)
        embedded_count = 0

        for i in range(0, total_to_embed, batch_size):
            batch = chunks_to_embed[i : i + batch_size]
            embeddings = await self.embed_passages([chunk.text for chunk in batch])
            for chunk, embedding in zip(batch, embeddings, strict=True):
                db.add(
                    CodeEmbedding(
                        chunk_id=chunk.id,
                        provider=settings.EMBEDDING_PROVIDER,
                        model=self.provider.model_name,
                        dimensions=settings.EMBEDDING_DIM,
                        embedding=embedding,
                    )
                )
            await db.flush()
            embedded_count += len(batch)
            if callable(progress_callback):
                await progress_callback(embedded_count, total_to_embed)

        return embedded_count

    async def _get_existing_embedding(
        self, db: AsyncSession, chunk: CodeChunk
    ) -> CodeEmbedding | None:
        if chunk.id is None:
            return None
        result = await db.execute(
            select(CodeEmbedding).where(CodeEmbedding.chunk_id == chunk.id)
        )
        return result.scalars().first()
