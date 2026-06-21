from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.dependency_graph import DependencyEdgeData, DependencyGraph
from app.analysis.file_classifier import FileClassifier
from app.analysis.languages import Language
from app.analysis.parser_models import ParsedFile, ParsedSymbol
from app.analysis.python_parser import PythonParser
from app.analysis.ts_js_parser import TsJsParser
from app.core.config import settings
from app.core.errors import GitOperationError, InvalidPathError, RepositoryNotFoundError
from app.core.security import validate_and_resolve_path
from app.db.models import (
    CodeChunk,
    CodeFile,
    Commit,
    DependencyEdge,
    Repository,
    Symbol,
)
from app.embeddings.service import EmbeddingService
from app.schemas.indexing import IndexRepositoryResponse, IndexStatusResponse
from app.services.git_service import GitService
from app.utils.hashing import compute_normalized_hash


class IndexingService:
    """Index repository files, parser output, chunks, dependencies, and commits."""

    def __init__(
        self,
        git_service: GitService,
        classifier: FileClassifier | None = None,
        graph_builder: DependencyGraph | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.git_service = git_service
        self.classifier = classifier or FileClassifier()
        self.graph_builder = graph_builder or DependencyGraph()
        self.embedding_service = embedding_service or EmbeddingService()
        self.python_parser = PythonParser()
        self.ts_js_parser = TsJsParser()

    async def index_repository(
        self,
        db: AsyncSession,
        repository_id: int,
        ref: str | None = None,
        max_commits: int | None = None,
    ) -> IndexRepositoryResponse:
        repo_obj = await self._get_repository_or_raise(db, repository_id)
        repo_path = self._validated_repo_path(repo_obj)

        repo_obj.status = "indexing"
        await db.flush()

        parser_errors: list[dict[str, Any]] = []
        warnings: list[str] = []
        skipped = 0
        parsed_files: list[ParsedFile] = []
        file_contents: dict[str, str] = {}
        code_files_by_path: dict[str, CodeFile] = {}
        symbol_records_by_key: dict[tuple[str, str, int], Symbol] = {}

        try:
            git_repo = self.git_service.open_repository(repo_path)
            if ref:
                self.git_service.checkout_ref(git_repo, ref)
            current_sha = self.git_service.get_current_sha(git_repo)
            tracked_files = self.git_service.list_tracked_files(git_repo)

            await self._clear_index_rows(db, repository_id)

            for tracked_path in tracked_files:
                full_path = repo_path / tracked_path
                if self._should_skip_path(full_path, tracked_path):
                    skipped += 1
                    continue

                content_bytes = full_path.read_bytes()
                if self.git_service.is_binary_file(content=content_bytes):
                    skipped += 1
                    continue

                content = content_bytes.decode("utf-8", errors="replace")
                classification = self.classifier.classify(tracked_path, content)
                if (
                    classification["should_ignore"]
                    or classification["is_generated"]
                    or not classification["is_supported"]
                ):
                    skipped += 1
                    continue

                parsed = self._parse_file(
                    tracked_path,
                    content,
                    classification["language"],
                )
                if parsed.errors:
                    parser_errors.append(
                        {
                            "path": tracked_path,
                            "errors": [
                                {
                                    "message": error.message,
                                    "line": error.line,
                                    "column": error.column,
                                }
                                for error in parsed.errors
                            ],
                        }
                    )

                code_file = await self._upsert_code_file(
                    db=db,
                    repository_id=repository_id,
                    path=tracked_path,
                    language=classification["language"],
                    content=content,
                    loc=int(classification["loc"]),
                    is_test=bool(classification["is_test"]),
                    is_generated=bool(classification["is_generated"]),
                    last_seen_commit=current_sha,
                    parser_errors=parser_errors[-1:] if parsed.errors else [],
                )
                code_files_by_path[tracked_path] = code_file
                parsed_files.append(parsed)
                file_contents[tracked_path] = content

            symbols_indexed = await self._save_symbols(
                db, repository_id, parsed_files, code_files_by_path, symbol_records_by_key
            )
            chunks_indexed, chunks = await self._save_chunks(
                db,
                repository_id,
                parsed_files,
                code_files_by_path,
                symbol_records_by_key,
                file_contents,
            )
            embeddings_indexed = await self.embedding_service.save_embeddings_for_chunks(
                db, chunks
            )
            edges = self.graph_builder.build_edges(
                parsed_files, set(code_files_by_path)
            )
            dependency_edges_indexed = await self._save_dependency_edges(
                db,
                repository_id,
                edges,
                code_files_by_path,
            )
            commits_indexed = await self._save_commit_metadata(
                db,
                repository_id,
                git_repo,
                max_commits or settings.MAX_COMMITS_TO_MINE,
            )

            repo_obj.current_ref = current_sha
            repo_obj.last_indexed_commit = current_sha
            repo_obj.indexed_at = datetime.now(timezone.utc)
            repo_obj.status = "indexed"
            await db.commit()
            await db.refresh(repo_obj)

            return IndexRepositoryResponse(
                repository_id=repository_id,
                status=repo_obj.status,
                current_ref=repo_obj.current_ref,
                indexed_at=repo_obj.indexed_at,
                files_indexed=len(code_files_by_path),
                files_skipped=skipped,
                symbols_indexed=symbols_indexed,
                chunks_indexed=chunks_indexed,
                embeddings_indexed=embeddings_indexed,
                dependency_edges_indexed=dependency_edges_indexed,
                commits_indexed=commits_indexed,
                parser_errors=parser_errors,
                warnings=warnings,
            )
        except Exception as exc:
            await db.rollback()
            repo_obj = await self._get_repository_or_raise(db, repository_id)
            repo_obj.status = "index_failed"
            repo_obj.repo_metadata = {
                **(repo_obj.repo_metadata or {}),
                "last_index_error": str(exc),
            }
            await db.commit()
            if isinstance(exc, (GitOperationError, InvalidPathError)):
                raise
            raise GitOperationError(f"Failed to index repository: {exc}") from exc

    async def get_index_status(
        self, db: AsyncSession, repository_id: int
    ) -> IndexStatusResponse:
        repo_obj = await self._get_repository_or_raise(db, repository_id)
        return IndexStatusResponse(
            repository_id=repository_id,
            status=repo_obj.status,
            current_ref=repo_obj.current_ref,
            last_indexed_commit=repo_obj.last_indexed_commit,
            indexed_at=repo_obj.indexed_at,
            file_count=await self._count(db, CodeFile, repository_id),
            symbol_count=await self._count(db, Symbol, repository_id),
            chunk_count=await self._count(db, CodeChunk, repository_id),
            dependency_edge_count=await self._count(db, DependencyEdge, repository_id),
            commit_count=await self._count(db, Commit, repository_id),
        )

    async def _get_repository_or_raise(
        self, db: AsyncSession, repository_id: int
    ) -> Repository:
        repo_obj = await db.get(Repository, repository_id)
        if repo_obj is None:
            raise RepositoryNotFoundError(
                f"Repository with id={repository_id} does not exist"
            )
        return repo_obj

    def _validated_repo_path(self, repo_obj: Repository) -> Path:
        if not repo_obj.local_path:
            raise InvalidPathError("Repository has no local_path to index.")
        repo_path = validate_and_resolve_path(repo_obj.local_path)
        if not repo_path.exists():
            raise InvalidPathError(f"Repository path does not exist: {repo_path}")
        return repo_path

    def _should_skip_path(self, full_path: Path, tracked_path: str) -> bool:
        if not full_path.is_file():
            return True
        max_bytes = settings.MAX_INDEX_FILE_SIZE_KB * 1024
        try:
            return full_path.stat().st_size > max_bytes
        except OSError:
            return True

    def _parse_file(
        self, path: str, content: str, language: object
    ) -> ParsedFile:
        if language is Language.PYTHON:
            return self.python_parser.parse(path, content)
        if language in {Language.JAVASCRIPT, Language.TYPESCRIPT}:
            return self.ts_js_parser.parse(path, content)
        return ParsedFile(path=path, language=Language.UNKNOWN)

    async def _clear_index_rows(self, db: AsyncSession, repository_id: int) -> None:
        file_ids = (
            await db.execute(
                select(CodeFile.id).where(CodeFile.repository_id == repository_id)
            )
        ).scalars().all()
        if file_ids:
            await db.execute(delete(CodeChunk).where(CodeChunk.file_id.in_(file_ids)))
            await db.execute(delete(Symbol).where(Symbol.file_id.in_(file_ids)))
            await db.execute(
                delete(DependencyEdge).where(
                    DependencyEdge.repository_id == repository_id
                )
            )
        await db.execute(delete(CodeFile).where(CodeFile.repository_id == repository_id))
        await db.execute(delete(Commit).where(Commit.repository_id == repository_id))
        await db.flush()

    async def _upsert_code_file(
        self,
        db: AsyncSession,
        repository_id: int,
        path: str,
        language: object,
        content: str,
        loc: int,
        is_test: bool,
        is_generated: bool,
        last_seen_commit: str,
        parser_errors: list[dict[str, Any]],
    ) -> CodeFile:
        code_file = CodeFile(
            repository_id=repository_id,
            path=Path(path).as_posix(),
            language=str(language.value if isinstance(language, Language) else language),
            content_hash=compute_normalized_hash(content),
            loc=loc,
            is_test=is_test,
            is_generated=is_generated,
            last_seen_commit=last_seen_commit,
            file_metadata={"parser_errors": parser_errors} if parser_errors else {},
        )
        db.add(code_file)
        await db.flush()
        return code_file

    async def _save_symbols(
        self,
        db: AsyncSession,
        repository_id: int,
        parsed_files: list[ParsedFile],
        code_files_by_path: dict[str, CodeFile],
        symbol_records_by_key: dict[tuple[str, str, int], Symbol],
    ) -> int:
        count = 0
        for parsed in parsed_files:
            code_file = code_files_by_path.get(parsed.path)
            if code_file is None:
                continue
            for parsed_symbol in parsed.symbols:
                symbol = Symbol(
                    repository_id=repository_id,
                    file_id=code_file.id,
                    qualified_name=parsed_symbol.qualified_name,
                    simple_name=parsed_symbol.simple_name,
                    symbol_type=parsed_symbol.symbol_type,
                    start_line=parsed_symbol.start_line,
                    end_line=parsed_symbol.end_line,
                    signature=parsed_symbol.signature,
                    docstring=parsed_symbol.docstring,
                    content_hash=compute_normalized_hash(
                        self._symbol_identity(parsed_symbol)
                    ),
                    symbol_metadata={
                        "decorators": parsed_symbol.decorators,
                        "bases": parsed_symbol.bases,
                        "is_test": parsed_symbol.is_test,
                        **parsed_symbol.metadata,
                    },
                )
                db.add(symbol)
                await db.flush()
                symbol_records_by_key[
                    (parsed.path, parsed_symbol.qualified_name, parsed_symbol.start_line)
                ] = symbol
                count += 1
        return count

    async def _save_chunks(
        self,
        db: AsyncSession,
        repository_id: int,
        parsed_files: list[ParsedFile],
        code_files_by_path: dict[str, CodeFile],
        symbol_records_by_key: dict[tuple[str, str, int], Symbol],
        file_contents: dict[str, str],
    ) -> tuple[int, list[CodeChunk]]:
        count = 0
        chunks: list[CodeChunk] = []
        for parsed in parsed_files:
            code_file = code_files_by_path.get(parsed.path)
            content = file_contents.get(parsed.path, "")
            if code_file is None:
                continue
            symbols = parsed.symbols or [
                ParsedSymbol(
                    qualified_name=Path(parsed.path).stem,
                    simple_name=Path(parsed.path).stem,
                    symbol_type="module",
                    start_line=1,
                    end_line=max(len(content.splitlines()), 1),
                )
            ]
            for parsed_symbol in symbols:
                symbol = symbol_records_by_key.get(
                    (parsed.path, parsed_symbol.qualified_name, parsed_symbol.start_line)
                )
                text = self._chunk_text(parsed, parsed_symbol, content)
                chunk = CodeChunk(
                    repository_id=repository_id,
                    file_id=code_file.id,
                    symbol_id=symbol.id if symbol else None,
                    chunk_type=self._chunk_type(parsed_symbol),
                    text=text,
                    start_line=parsed_symbol.start_line,
                    end_line=parsed_symbol.end_line,
                    content_hash=compute_normalized_hash(text),
                    token_count_estimate=max(len(text) // 4, 1),
                )
                db.add(chunk)
                chunks.append(chunk)
                count += 1
        await db.flush()
        return count, chunks

    async def _save_dependency_edges(
        self,
        db: AsyncSession,
        repository_id: int,
        edges: list[DependencyEdgeData],
        code_files_by_path: dict[str, CodeFile],
    ) -> int:
        count = 0
        for edge in edges:
            source = code_files_by_path.get(edge.source_path)
            target = code_files_by_path.get(edge.target_path)
            if source is None or target is None:
                continue
            db.add(
                DependencyEdge(
                    repository_id=repository_id,
                    source_file_id=source.id,
                    target_file_id=target.id,
                    edge_type=edge.edge_type,
                    confidence=edge.confidence,
                    evidence=edge.evidence,
                )
            )
            count += 1
        await db.flush()
        return count

    async def _save_commit_metadata(
        self,
        db: AsyncSession,
        repository_id: int,
        git_repo: Any,
        max_commits: int,
    ) -> int:
        count = 0
        for commit in self.git_service.iter_commits(git_repo, max_count=max_commits):
            metadata = self.git_service.get_commit_metadata(git_repo, commit.hexsha)
            db.add(
                Commit(
                    repository_id=repository_id,
                    sha=metadata["sha"],
                    parent_sha=metadata.get("parent_sha"),
                    author_name=metadata.get("author_name"),
                    author_email=metadata.get("author_email"),
                    author_date=metadata.get("author_date"),
                    message=metadata.get("message"),
                    changed_files=self._commit_changed_files(commit),
                    insertions=metadata.get("insertions"),
                    deletions=metadata.get("deletions"),
                )
            )
            count += 1
        await db.flush()
        return count

    async def _count(
        self, db: AsyncSession, model: type[Any], repository_id: int
    ) -> int:
        result = await db.execute(
            select(func.count()).select_from(model).where(
                model.repository_id == repository_id
            )
        )
        return int(result.scalar_one())

    def _chunk_text(
        self, parsed: ParsedFile, symbol: ParsedSymbol, content: str
    ) -> str:
        lines = content.splitlines()
        body = "\n".join(lines[symbol.start_line - 1 : symbol.end_line])
        return "\n".join(
            [
                f"path: {parsed.path}",
                f"language: {parsed.language.value}",
                f"symbol: {symbol.qualified_name}",
                f"signature: {symbol.signature or ''}",
                "",
                body,
            ]
        )

    def _chunk_type(self, symbol: ParsedSymbol) -> str:
        if symbol.is_test:
            return "test"
        if symbol.symbol_type in {"function", "class", "method"}:
            return symbol.symbol_type
        return "file"

    def _symbol_identity(self, symbol: ParsedSymbol) -> str:
        return "|".join(
            [
                symbol.qualified_name,
                symbol.symbol_type,
                str(symbol.start_line),
                str(symbol.end_line),
                symbol.signature or "",
            ]
        )

    def _commit_changed_files(self, commit: Any) -> list[dict[str, Any]]:
        try:
            return [
                {"path": path, **stats}
                for path, stats in commit.stats.files.items()
            ]
        except Exception:
            return []
