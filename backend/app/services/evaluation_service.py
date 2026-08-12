from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.cochange import CochangeMiner
from app.analysis.evaluation_metrics import EvaluationMetrics
from app.core.errors import RepositoryNotFoundError
from app.db.models import (
    CodeFile,
    Commit,
    DependencyEdge,
    EvaluationResult,
    EvaluationRun,
    Repository,
)
from app.schemas.evaluation import (
    EvaluationReportResponse,
    EvaluationRunRequest,
    EvaluationRunResponse,
    EvaluationStatusResponse,
)
from app.services.semantic_search_service import SemanticSearchService


class EvaluationService:
    """Run historical commit evaluation against indexed GitVane evidence."""

    def __init__(
        self,
        semantic_search_service: SemanticSearchService | None = None,
    ) -> None:
        self.metrics = EvaluationMetrics()
        self.cochange_miner = CochangeMiner()
        self.semantic_search_service = semantic_search_service

    async def run_evaluation(
        self,
        db: AsyncSession,
        request: EvaluationRunRequest,
    ) -> EvaluationRunResponse:
        await self._get_repository_or_raise(db, request.repository_id)
        evaluation_run = EvaluationRun(
            repository_id=request.repository_id,
            name=request.name,
            status="running",
            base_method="multiple",
            commit_limit=request.commit_limit,
            config={
                "methods": request.methods,
                "k_values": request.k_values,
                "limitation": "Uses the current indexed graph as an approximation.",
            },
        )
        db.add(evaluation_run)
        await db.commit()
        await db.refresh(evaluation_run)

        await self.execute_evaluation(
            db=db,
            evaluation_run_id=evaluation_run.id,
            commit_limit=request.commit_limit,
            methods=request.methods,
            k_values=request.k_values,
        )

        await db.refresh(evaluation_run)
        summary = (evaluation_run.config or {}).get("summary", {})
        return EvaluationRunResponse(
            evaluation_run_id=evaluation_run.id,
            status=evaluation_run.status,
            summary=summary,
        )

    async def get_evaluation_run_repository_id(
        self, db: AsyncSession, evaluation_run_id: int
    ) -> UUID:
        """Get the repository_id for an evaluation run, raising RepositoryNotFoundError if missing."""
        stmt = select(EvaluationRun.repository_id).where(EvaluationRun.id == evaluation_run_id)
        result = await db.execute(stmt)
        repository_id = result.scalar_one_or_none()
        if repository_id is None:
            raise RepositoryNotFoundError(f"Evaluation run with id={evaluation_run_id} does not exist")
        return repository_id

    async def execute_evaluation(
        self,
        db: AsyncSession,
        evaluation_run_id: int,
        commit_limit: int,
        methods: list[str],
        k_values: list[int],
    ) -> None:
        evaluation_run = await db.get(EvaluationRun, evaluation_run_id)
        if evaluation_run is None:
            raise RepositoryNotFoundError(
                f"Evaluation run with id={evaluation_run_id} does not exist"
            )

        try:
            code_files, edges, commits = await self._load_indexed_data(
                db, evaluation_run.repository_id, commit_limit
            )
            code_paths = {item.path for item in code_files}
            scenarios, skipped = self._build_scenarios(commits, code_paths)
            results: list[dict[str, Any]] = []
            method_summaries: dict[str, list[dict[str, float]]] = {
                method: [] for method in methods
            }

            for scenario in scenarios:
                method_predictions: dict[str, list[str]] = {}
                method_metrics: dict[str, dict[str, float]] = {}
                for method in methods:
                    predictions = await self._predict(
                        db,
                        evaluation_run.repository_id,
                        method,
                        scenario["known_file"],
                        code_files,
                        edges,
                        commits,
                    )
                    method_predictions[method] = predictions
                    computed = self.metrics.all_at_k(
                        predictions,
                        set(scenario["ground_truth"]),
                        k_values,
                    )
                    method_metrics[method] = computed
                    method_summaries[method].append(computed)

                db.add(
                    EvaluationResult(
                        evaluation_run_id=evaluation_run.id,
                        commit_sha=scenario["commit_sha"],
                        scenario=scenario,
                        metrics=method_metrics,
                        predictions=method_predictions,
                        ground_truth=scenario["ground_truth"],
                    )
                )
                results.append(
                    {
                        "scenario": scenario,
                        "metrics": method_metrics,
                        "predictions": method_predictions,
                    }
                )

            summary = self._summary(method_summaries, len(scenarios), skipped)
            evaluation_run.status = "completed"
            evaluation_run.config = {
                **(evaluation_run.config or {}),
                "summary": summary,
            }
            evaluation_run.finished_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            evaluation_run.status = "failed"
            evaluation_run.error_message = str(exc)
            evaluation_run.finished_at = datetime.now(timezone.utc)
            db.add(evaluation_run)
            await db.commit()
            raise

    async def get_evaluation(
        self, db: AsyncSession, evaluation_run_id: int
    ) -> EvaluationStatusResponse:
        run = await db.get(EvaluationRun, evaluation_run_id)
        if run is None:
            raise RepositoryNotFoundError(
                f"Evaluation run with id={evaluation_run_id} does not exist"
            )
        config = run.config or {}
        return EvaluationStatusResponse(
            evaluation_run_id=run.id,
            repository_id=run.repository_id,
            name=run.name,
            status=run.status,
            methods=list(config.get("methods", [])),
            commit_limit=run.commit_limit,
            summary=dict(config.get("summary", {})),
            error_message=run.error_message,
        )

    async def get_report(
        self, db: AsyncSession, evaluation_run_id: int
    ) -> EvaluationReportResponse:
        run = await db.get(EvaluationRun, evaluation_run_id)
        if run is None:
            raise RepositoryNotFoundError(
                f"Evaluation run with id={evaluation_run_id} does not exist"
            )
        result = await db.execute(
            select(EvaluationResult)
            .where(EvaluationResult.evaluation_run_id == evaluation_run_id)
            .order_by(EvaluationResult.id)
        )
        results = list(result.scalars().all())
        markdown = self._render_report(run, results)
        return EvaluationReportResponse(
            evaluation_run_id=evaluation_run_id,
            markdown=markdown,
        )

    async def _load_indexed_data(
        self, db: AsyncSession, repository_id: UUID | Any, commit_limit: int
    ) -> tuple[list[CodeFile], list[DependencyEdge], list[Commit]]:
        repo_obj = await self._get_repository_or_raise(db, repository_id)
        commits = (
            await db.execute(
                select(Commit)
                .where(Commit.repository_id == repository_id)
                .order_by(Commit.author_date.desc().nullslast())
                .limit(commit_limit)
            )
        ).scalars().all()
        if repo_obj.active_generation_id is None:
            return [], [], list(commits)

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
        return list(code_files), list(edges), list(commits)

    def _build_scenarios(
        self, commits: list[Commit], code_paths: set[str]
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        scenarios: list[dict[str, Any]] = []
        skipped = {
            "fewer_than_two_code_files": 0,
            "too_many_files": 0,
            "no_indexed_code_files": 0,
        }
        for commit in commits:
            paths = sorted(self._commit_paths(commit) & code_paths)
            if not paths:
                skipped["no_indexed_code_files"] += 1
                continue
            if len(paths) < 2:
                skipped["fewer_than_two_code_files"] += 1
                continue
            if len(paths) > 20:
                skipped["too_many_files"] += 1
                continue
            known = paths[-1]
            scenarios.append(
                {
                    "commit_sha": commit.sha,
                    "known_file": known,
                    "ground_truth": [path for path in paths if path != known],
                    "changed_files": paths,
                    "approximation": "current_index",
                }
            )
        return scenarios, skipped

    async def _predict(
        self,
        db: AsyncSession,
        repository_id: UUID | Any,
        method: str,
        known_file: str,
        code_files: list[CodeFile],
        edges: list[DependencyEdge],
        commits: list[Commit],
    ) -> list[str]:
        if method == "dependency_only":
            return self._dependency_predictions(known_file, code_files, edges)
        if method == "cochange_only":
            return self._cochange_predictions(known_file, commits)
        if method == "semantic_only":
            return await self._semantic_predictions(db, repository_id, known_file)
        dependency = self._dependency_predictions(known_file, code_files, edges)
        cochange = self._cochange_predictions(known_file, commits)
        semantic = await self._semantic_predictions(db, repository_id, known_file)
        return self._hybrid_predictions([dependency, cochange, semantic])

    def _dependency_predictions(
        self,
        known_file: str,
        code_files: list[CodeFile],
        edges: list[DependencyEdge],
    ) -> list[str]:
        files_by_id = {item.id: item for item in code_files}
        reverse: dict[str, set[str]] = {}
        for edge in edges:
            source = files_by_id.get(edge.source_file_id)
            target = files_by_id.get(edge.target_file_id)
            if source is None or target is None:
                continue
            reverse.setdefault(target.path, set()).add(source.path)
        return sorted(reverse.get(known_file, set()))

    def _cochange_predictions(self, known_file: str, commits: list[Commit]) -> list[str]:
        scores = self.cochange_miner.score_candidates({known_file}, commits)
        return [
            path
            for path, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        ]

    async def _semantic_predictions(
        self, db: AsyncSession, repository_id: UUID | Any, known_file: str
    ) -> list[str]:
        if self.semantic_search_service is None:
            return []
        try:
            response = await self.semantic_search_service.semantic_search(
                db=db,
                repository_id=repository_id,
                query=known_file,
                top_k=20,
            )
        except Exception:
            return []
        return [item.path for item in response.results if item.path != known_file]

    def _hybrid_predictions(self, ranked_lists: list[list[str]]) -> list[str]:
        scores: dict[str, float] = {}
        for ranked in ranked_lists:
            for index, path in enumerate(ranked, start=1):
                scores[path] = scores.get(path, 0.0) + 1 / index
        return [
            path
            for path, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        ]

    def _summary(
        self,
        method_summaries: dict[str, list[dict[str, float]]],
        evaluated_commits: int,
        skipped: dict[str, int],
    ) -> dict[str, Any]:
        methods = {
            method: self._average_metrics(rows)
            for method, rows in method_summaries.items()
        }
        return {
            "evaluated_commits": evaluated_commits,
            "skipped_commits": sum(skipped.values()),
            "skipped_reasons": skipped,
            "methods": methods,
            "limitation": (
                "MVP evaluation uses the current indexed graph as an approximation "
                "instead of checking out each historical commit."
            ),
        }

    def _average_metrics(self, rows: list[dict[str, float]]) -> dict[str, float]:
        if not rows:
            return {}
        keys = sorted({key for row in rows for key in row})
        return {
            key: round(sum(row.get(key, 0.0) for row in rows) / len(rows), 4)
            for key in keys
        }

    def _render_report(
        self, run: EvaluationRun, results: list[EvaluationResult]
    ) -> str:
        config = run.config or {}
        summary = config.get("summary", {})
        lines = [
            f"# Evaluation Report: {run.name}",
            "",
            f"- Repository ID: {run.repository_id}",
            f"- Status: {run.status}",
            f"- Evaluated commits: {summary.get('evaluated_commits', 0)}",
            f"- Skipped commits: {summary.get('skipped_commits', 0)}",
            "- Limitation: current indexed graph approximation is used.",
            "",
            "## Metrics",
            "",
        ]
        methods = summary.get("methods", {})
        for method, metrics in methods.items():
            lines.append(f"### {method}")
            if not metrics:
                lines.append("No eligible scenarios.")
            else:
                for key, value in sorted(metrics.items()):
                    lines.append(f"- {key}: {value}")
            lines.append("")

        lines.extend(
            [
                "## Interpretation",
                "",
                "Higher recall means the method found more files that historically "
                "changed together. Higher precision means fewer unrelated files were "
                "recommended. Poor scores are reported as-is.",
                "",
                "## Example Cases",
                "",
            ]
        )
        if results:
            first = results[0]
            lines.extend(
                [
                    f"- Example commit: {first.commit_sha}",
                    f"- Known file: {first.scenario.get('known_file') if first.scenario else None}",
                    f"- Ground truth: {first.ground_truth}",
                ]
            )
        else:
            lines.append("No eligible scenarios were evaluated.")
        return "\n".join(lines)

    def _commit_paths(self, commit: Commit) -> set[str]:
        paths: set[str] = set()
        for item in commit.changed_files or []:
            if isinstance(item, str):
                paths.add(item)
            elif isinstance(item, dict) and item.get("path"):
                paths.add(str(item["path"]))
        return paths

    async def _get_repository_or_raise(
        self, db: AsyncSession, repository_id: UUID | Any
    ) -> Repository:
        repo_obj = await db.get(Repository, repository_id)
        if repo_obj is None:
            raise RepositoryNotFoundError(
                f"Repository with id={repository_id} does not exist"
            )
        return repo_obj
