from typing import Protocol


class EmbeddingProvider(Protocol):
    """Protocol defining the interface for all embedding providers"""

    async def embed_passages(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple passages"""
        ...

    async def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a single search or change query"""
        ...

    @property
    def model_name(self) -> str:
        """Name of the model being utilized"""
        ...

    @property
    def dimensions(self) -> int:
        """Dimensionality of output vectors"""
        ...
