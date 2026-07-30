from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import RepositoryNotFoundError
from app.db.models import CodeFile, DependencyEdge, Repository
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse


class GraphService:
    """Build graph API responses from indexed dependency rows."""

    async def get_file_neighbors(
        self,
        db: AsyncSession,
        repository_id: UUID | Any,
        file_id: int,
    ) -> GraphResponse:
        await self._ensure_repository(db, repository_id)
        center = await db.get(CodeFile, file_id)
        if center is None or center.repository_id != repository_id:
            raise RepositoryNotFoundError(
                f"File with id={file_id} does not exist in repository {repository_id}"
            )

        edge_result = await db.execute(
            select(DependencyEdge).where(
                DependencyEdge.repository_id == repository_id,
                or_(
                    DependencyEdge.source_file_id == file_id,
                    DependencyEdge.target_file_id == file_id,
                ),
            )
        )
        edges = list(edge_result.scalars().all())
        file_ids = {file_id}
        for edge in edges:
            file_ids.add(edge.source_file_id)
            file_ids.add(edge.target_file_id)

        nodes = await self._load_files(db, repository_id, file_ids)
        return self._response(repository_id, nodes, edges)

    async def get_repository_subgraph(
        self,
        db: AsyncSession,
        repository_id: UUID | Any,
        max_nodes: int = 500,
        language: str | None = None,
        include_tests: bool = True,
    ) -> GraphResponse:
        await self._ensure_repository(db, repository_id)
        stmt = (
            select(CodeFile)
            .where(CodeFile.repository_id == repository_id)
            .order_by(CodeFile.path)
            .limit(max_nodes)
        )
        if language:
            stmt = stmt.where(CodeFile.language == language)
        if not include_tests:
            stmt = stmt.where(CodeFile.is_test.is_(False))

        file_result = await db.execute(stmt)
        nodes = list(file_result.scalars().all())
        file_ids = {node.id for node in nodes}
        if not file_ids:
            return GraphResponse(repository_id=repository_id, nodes=[], edges=[])

        edge_result = await db.execute(
            select(DependencyEdge).where(
                DependencyEdge.repository_id == repository_id,
                DependencyEdge.source_file_id.in_(file_ids),
                DependencyEdge.target_file_id.in_(file_ids),
            )
        )
        edges = list(edge_result.scalars().all())
        return self._response(repository_id, nodes, edges)

    async def _ensure_repository(self, db: AsyncSession, repository_id: UUID | Any) -> None:
        repo = await db.get(Repository, repository_id)
        if repo is None:
            raise RepositoryNotFoundError(
                f"Repository with id={repository_id} does not exist"
            )

    async def _load_files(
        self, db: AsyncSession, repository_id: UUID | Any, file_ids: set[int]
    ) -> list[CodeFile]:
        if not file_ids:
            return []
        result = await db.execute(
            select(CodeFile)
            .where(
                CodeFile.repository_id == repository_id,
                CodeFile.id.in_(file_ids),
            )
            .order_by(CodeFile.path)
        )
        return list(result.scalars().all())

    def _response(
        self,
        repository_id: UUID | Any,
        files: list[CodeFile],
        edges: list[DependencyEdge],
    ) -> GraphResponse:
        files_by_id = {file.id: file for file in files}
        graph_edges = [
            self._edge(edge, files_by_id)
            for edge in edges
            if edge.source_file_id in files_by_id and edge.target_file_id in files_by_id
        ]
        return GraphResponse(
            repository_id=repository_id,
            nodes=[self._node(file) for file in files],
            edges=graph_edges,
        )

    def _node(self, file: CodeFile) -> GraphNode:
        return GraphNode(
            id=file.id,
            path=file.path,
            language=file.language,
            is_test=bool(file.is_test),
            is_generated=bool(file.is_generated),
            loc=int(file.loc or 0),
        )

    def _edge(
        self,
        edge: DependencyEdge,
        files_by_id: dict[int, CodeFile],
    ) -> GraphEdge:
        return GraphEdge(
            id=edge.id,
            source_file_id=edge.source_file_id,
            target_file_id=edge.target_file_id,
            source_path=files_by_id[edge.source_file_id].path,
            target_path=files_by_id[edge.target_file_id].path,
            edge_type=edge.edge_type,
            confidence=float(edge.confidence),
            evidence=edge.evidence or {},
        )
