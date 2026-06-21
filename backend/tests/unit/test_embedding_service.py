import pytest

from app.core.config import settings
from app.core.errors import EmbeddingDimensionMismatchError
from app.db.models import CodeChunk, CodeEmbedding
from app.embeddings.service import EmbeddingService


class _FakeProvider:
    def __init__(self, dimensions: int) -> None:
        self._dimensions = dimensions

    @property
    def model_name(self) -> str:
        return "fake-model"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * self._dimensions for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [0.1] * self._dimensions


class _ScalarResult:
    def __init__(self, value: CodeEmbedding | None) -> None:
        self.value = value

    def first(self) -> CodeEmbedding | None:
        return self.value


class _ExecuteResult:
    def __init__(self, value: CodeEmbedding | None) -> None:
        self.value = value

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self.value)


class _FakeDb:
    def __init__(self, existing: CodeEmbedding | None = None) -> None:
        self.existing = existing
        self.added: list[CodeEmbedding] = []

    async def execute(self, statement: object) -> _ExecuteResult:
        return _ExecuteResult(self.existing)

    def add(self, obj: CodeEmbedding) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        pass


def test_validate_embedding_rejects_dimension_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "EMBEDDING_DIM", 3)
    service = EmbeddingService(_FakeProvider(dimensions=2))

    with pytest.raises(EmbeddingDimensionMismatchError, match="regenerate migrations"):
        service.validate_embedding([0.1, 0.2])


@pytest.mark.asyncio()
async def test_embed_query_validates_provider_dimensions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "EMBEDDING_DIM", 2)
    service = EmbeddingService(_FakeProvider(dimensions=2))

    embedding = await service.embed_query("auth token")

    assert embedding == [0.1, 0.1]


@pytest.mark.asyncio()
async def test_save_embeddings_skips_existing_matching_embedding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "local")
    monkeypatch.setattr(settings, "EMBEDDING_DIM", 2)
    chunk = CodeChunk(id=1, text="path: src/auth.py", content_hash="abc")
    existing = CodeEmbedding(
        chunk_id=1,
        provider="local",
        model="fake-model",
        dimensions=2,
        embedding=[0.1, 0.1],
    )
    db = _FakeDb(existing=existing)
    service = EmbeddingService(_FakeProvider(dimensions=2))

    saved = await service.save_embeddings_for_chunks(db, [chunk])

    assert saved == 0
    assert db.added == []


@pytest.mark.asyncio()
async def test_save_embeddings_persists_missing_embedding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "local")
    monkeypatch.setattr(settings, "EMBEDDING_DIM", 2)
    chunk = CodeChunk(id=1, text="path: src/auth.py", content_hash="abc")
    db = _FakeDb(existing=None)
    service = EmbeddingService(_FakeProvider(dimensions=2))

    saved = await service.save_embeddings_for_chunks(db, [chunk])

    assert saved == 1
    assert len(db.added) == 1
    assert db.added[0].embedding == [0.1, 0.1]
