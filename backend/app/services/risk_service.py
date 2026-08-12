from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.complexity import ComplexityCalculator
from app.analysis.languages import Language
from app.core.errors import RepositoryNotFoundError
from app.db.models import CodeChunk, CodeFile, Commit, DependencyEdge, Repository
from app.schemas.risk import RepositoryRiskResponse, RiskFileOut


@dataclass(frozen=True)
class FileRisk:
    path: str
    score: float
    components: dict[str, float]
    reasons: list[str] = field(default_factory=list)


class RiskService:
    """Compute heuristic file risk from indexed metadata."""

    BUGFIX_KEYWORDS = ("fix", "bug", "regression", "hotfix", "patch", "broken")

    def __init__(self, complexity_calculator: ComplexityCalculator | None = None) -> None:
        self.complexity_calculator = complexity_calculator or ComplexityCalculator()

    async def get_repository_file_risks(
        self,
        db: AsyncSession,
        repository_id: UUID | Any,
        top_k: int = 20,
        language: str | None = None,
        include_tests: bool = False,
        path_search: str | None = None,
    ) -> RepositoryRiskResponse:
        repo_obj = await db.get(Repository, repository_id)
        if repo_obj is None:
            raise RepositoryNotFoundError(
                f"Repository with id={repository_id} does not exist"
            )

        code_files, edges, commits, chunks = await self._load_indexed_data(
            db, repository_id
        )
        fan_in, fan_out = self._fan_counts(edges)
        churn = self._churn_counts(commits)
        chunk_text_by_file = self._chunk_text_by_file(chunks)

        risks: list[FileRisk] = []
        for code_file in code_files:
            if not include_tests and code_file.is_test:
                continue
            if language and code_file.language != language:
                continue
            content = chunk_text_by_file.get(code_file.id, "")
            complexity = self.complexity_calculator.score(
                content,
                code_file.language or Language.UNKNOWN.value,
            )
            risks.append(
                self.score_file(
                    code_file,
                    fan_in=fan_in.get(code_file.id, 0),
                    fan_out=fan_out.get(code_file.id, 0),
                    churn=churn.get(code_file.path, 0),
                    bugfix_churn=self.bugfix_churn_for_file(code_file.path, commits),
                    complexity=complexity,
                )
            )

        mean_risk_score = (
            round(sum(item.score for item in risks) / len(risks), 4)
            if risks
            else 0.0
        )

        filtered_risks = (
            [item for item in risks if path_search.lower() in item.path.lower()]
            if path_search
            else risks
        )

        ranked = sorted(filtered_risks, key=lambda item: (-item.score, item.path))[:top_k]
        return RepositoryRiskResponse(
            repository_id=repository_id,
            files=[
                RiskFileOut(
                    path=item.path,
                    risk_score=item.score,
                    components=item.components,
                    reasons=item.reasons,
                )
                for item in ranked
            ],
            metadata={
                "top_k": top_k,
                "language": language,
                "include_tests": include_tests,
                "path_search": path_search,
                "mean_risk_score": mean_risk_score,
            },
        )

    def score_file(
        self,
        code_file: CodeFile,
        fan_in: int = 0,
        fan_out: int = 0,
        churn: int = 0,
        bugfix_churn: int = 0,
        complexity: float = 0.0,
    ) -> FileRisk:
        loc = int(code_file.loc or 0)
        components = {
            "fan_in": self._scale(fan_in, 10),
            "fan_out": self._scale(fan_out, 10),
            "centrality": self._scale(fan_in + fan_out, 20),
            "churn": self._scale(churn, 20),
            "complexity": self._cap(complexity),
            "file_size": self._scale(loc, 500),
            "bugfix_frequency": self._scale(bugfix_churn, 8),
            "test_coverage_proxy": 0.2 if not code_file.is_test else 0.0,
        }
        score = round(
            min(
                1.0,
                components["fan_in"] * 0.25
                + components["fan_out"] * 0.10
                + components["centrality"] * 0.10
                + components["churn"] * 0.20
                + components["complexity"] * 0.15
                + components["file_size"] * 0.10
                + components["bugfix_frequency"] * 0.15
                + components["test_coverage_proxy"] * 0.05,
            ),
            4,
        )
        return FileRisk(
            path=code_file.path,
            score=score,
            components=components,
            reasons=self._reasons(components),
        )

    def bugfix_churn_for_file(self, path: str, commits: list[object]) -> int:
        count = 0
        for commit in commits:
            message = str(getattr(commit, "message", "") or "").lower()
            changed_files = getattr(commit, "changed_files", None) or []
            paths = {
                str(item.get("path"))
                for item in changed_files
                if isinstance(item, dict) and item.get("path")
            }
            if path in paths and any(keyword in message for keyword in self.BUGFIX_KEYWORDS):
                count += 1
        return count

    def _scale(self, value: int, saturation: int) -> float:
        if saturation <= 0:
            return 0.0
        return round(max(0.0, min(value / saturation, 1.0)), 4)

    def _reasons(self, components: dict[str, float]) -> list[str]:
        labels = {
            "fan_in": "High fan-in",
            "fan_out": "High fan-out",
            "centrality": "High graph centrality",
            "churn": "Frequently changed",
            "complexity": "High complexity",
            "file_size": "Large file",
            "bugfix_frequency": "Often touched by bugfix commits",
            "test_coverage_proxy": "Weak test proximity signal",
        }
        return [label for key, label in labels.items() if components.get(key, 0.0) >= 0.5]

    def _cap(self, value: float) -> float:
        return round(max(0.0, min(float(value), 1.0)), 4)

    async def _load_indexed_data(
        self, db: AsyncSession, repository_id: UUID | Any
    ) -> tuple[list[CodeFile], list[DependencyEdge], list[Commit], list[CodeChunk]]:
        repo_obj = await db.get(Repository, repository_id)
        if repo_obj is None:
            raise RepositoryNotFoundError(
                f"Repository with id={repository_id} does not exist"
            )

        commits = (
            await db.execute(select(Commit).where(Commit.repository_id == repository_id))
        ).scalars().all()
        if repo_obj.active_generation_id is None:
            return [], [], list(commits), []

        code_files = (
            await db.execute(
                select(CodeFile).where(
                    CodeFile.repository_id == repository_id,
                    CodeFile.generation_id == repo_obj.active_generation_id,
                )
            )
        ).scalars().all()
        edges = (
            await db.execute(
                select(DependencyEdge).where(
                    DependencyEdge.repository_id == repository_id,
                    DependencyEdge.generation_id == repo_obj.active_generation_id,
                )
            )
        ).scalars().all()
        chunks = (
            await db.execute(
                select(CodeChunk).where(
                    CodeChunk.repository_id == repository_id,
                    CodeChunk.generation_id == repo_obj.active_generation_id,
                )
            )
        ).scalars().all()
        return list(code_files), list(edges), list(commits), list(chunks)

    def _fan_counts(
        self, edges: list[DependencyEdge]
    ) -> tuple[dict[int, int], dict[int, int]]:
        fan_in: dict[int, int] = {}
        fan_out: dict[int, int] = {}
        for edge in edges:
            fan_out[edge.source_file_id] = fan_out.get(edge.source_file_id, 0) + 1
            fan_in[edge.target_file_id] = fan_in.get(edge.target_file_id, 0) + 1
        return fan_in, fan_out

    def _churn_counts(self, commits: list[Commit]) -> dict[str, int]:
        churn: dict[str, int] = {}
        for commit in commits:
            for item in commit.changed_files or []:
                if isinstance(item, dict) and item.get("path"):
                    path = str(item["path"])
                    churn[path] = churn.get(path, 0) + 1
        return churn

    def _chunk_text_by_file(self, chunks: list[CodeChunk]) -> dict[int, str]:
        grouped: dict[int, list[str]] = {}
        for chunk in chunks:
            grouped.setdefault(chunk.file_id, []).append(chunk.text)
        return {
            file_id: "\n".join(texts)
            for file_id, texts in grouped.items()
        }
