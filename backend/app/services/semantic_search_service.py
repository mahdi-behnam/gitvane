from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import RepositoryNotFoundError
from app.db.models import CodeChunk, CodeEmbedding, CodeFile, Repository, Symbol
from app.embeddings.service import EmbeddingService
from app.schemas.search import SemanticSearchResponse, SemanticSearchResult


class SemanticSearchService:
    """Search indexed code chunks using pgvector cosine similarity."""

    def __init__(self, embedding_service: EmbeddingService | None = None) -> None:
        self.embedding_service = embedding_service or EmbeddingService()

    async def semantic_search(
        self,
        db: AsyncSession,
        repository_id: int,
        query: str,
        top_k: int = 10,
    ) -> SemanticSearchResponse:
        repo_obj = await db.get(Repository, repository_id)
        if repo_obj is None:
            raise RepositoryNotFoundError(
                f"Repository with id={repository_id} does not exist"
            )

        query_embedding = await self.embedding_service.embed_query(query)
        distance = CodeEmbedding.embedding.cosine_distance(query_embedding).label(
            "distance"
        )
        stmt = (
            select(CodeChunk, CodeFile, Symbol, distance)
            .join(CodeFile, CodeChunk.file_id == CodeFile.id)
            .join(CodeEmbedding, CodeEmbedding.chunk_id == CodeChunk.id)
            .outerjoin(Symbol, CodeChunk.symbol_id == Symbol.id)
            .where(CodeChunk.repository_id == repository_id)
            .order_by(distance)
            .limit(top_k)
        )
        result = await db.execute(stmt)
        rows = result.all()
        return SemanticSearchResponse(
            results=[self._row_to_result(row) for row in rows]
        )

    def _row_to_result(self, row: Any) -> SemanticSearchResult:
        chunk, code_file, symbol, distance = row
        return SemanticSearchResult(
            path=code_file.path,
            symbol=symbol.qualified_name if symbol else None,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            score=self._distance_to_score(distance),
            snippet=self._snippet(chunk.text),
        )

    def _distance_to_score(self, distance: float | None) -> float:
        if distance is None:
            return 0.0
        return round(max(0.0, min(1.0, 1.0 - float(distance))), 4)

    def _snippet(self, text: str, max_chars: int = 600) -> str:
        normalized = "\n".join(line.rstrip() for line in text.strip().splitlines())
        if len(normalized) <= max_chars:
            return normalized
        return f"{normalized[: max_chars - 3].rstrip()}..."
