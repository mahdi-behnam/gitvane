from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.cochange import CochangeMiner
from app.analysis.diff_parser import ChangedFile, DiffParser
from app.analysis.scoring import CandidateScore, ImpactReason, ImpactScorer
from app.core.errors import GitOperationError, RepositoryNotFoundError
from app.db.models import (
    AnalysisRun,
    CodeFile,
    Commit,
    DependencyEdge,
    ImpactPrediction,
    Repository,
    Symbol,
)
from app.schemas.impact import (
    ChangedFileInput,
    ChangedSymbolOut,
    ImpactAnalyzeRequest,
    ImpactAnalyzeResponse,
    ImpactedFileOut,
    ImpactReasonOut,
    ImpactRunResponse,
    RiskSummaryOut,
    TestRecommendationOut,
)
from app.services.explanation_service import ExplanationService
from app.services.git_service import GitService
from app.services.risk_service import RiskService
from app.services.semantic_search_service import SemanticSearchService
from app.services.test_recommendation_service import TestRecommendationService


class ImpactService:
    """Compute deterministic impact predictions from indexed evidence."""

    def __init__(
        self,
        git_service: GitService,
        semantic_search_service: SemanticSearchService | None = None,
        risk_service: RiskService | None = None,
        test_service: TestRecommendationService | None = None,
        explanation_service: ExplanationService | None = None,
        scorer: ImpactScorer | None = None,
    ) -> None:
        self.git_service = git_service
        self.diff_parser = DiffParser()
        self.cochange_miner = CochangeMiner()
        self.semantic_search_service = semantic_search_service or SemanticSearchService()
        self.risk_service = risk_service or RiskService()
        self.test_service = test_service or TestRecommendationService()
        self.explanation_service = explanation_service or ExplanationService()
        self.scorer = scorer or ImpactScorer()

    async def analyze(
        self, db: AsyncSession, request: ImpactAnalyzeRequest
    ) -> ImpactAnalyzeResponse:
        repo_obj = await self._get_repository_or_raise(db, request.repository_id)
        changed_files = await self._resolve_changed_files(db, repo_obj, request)
        input_mode = self._input_mode(request)
        analysis_run = AnalysisRun(
            repository_id=request.repository_id,
            base_ref=request.base_ref,
            head_ref=request.head_ref,
            input_mode=input_mode,
            status="running",
            changed_files=[item.model_dump() for item in changed_files],
            config={
                "top_k": request.top_k,
                "include_changed_files_in_predictions": request.include_changed_files_in_predictions,
                "max_dependency_depth": request.max_dependency_depth,
            },
        )
        db.add(analysis_run)
        await db.flush()

        try:
            code_files, symbols, edges, commits = await self._load_indexed_data(
                db, request.repository_id
            )
            files_by_id = {code_file.id: code_file for code_file in code_files}
            changed_symbols = self._map_changed_symbols(
                changed_files, symbols, files_by_id
            )
            candidates = await self._score_candidates(
                db=db,
                repository_id=request.repository_id,
                changed_files=changed_files,
                changed_symbols=changed_symbols,
                code_files=code_files,
                edges=edges,
                commits=commits,
                include_changed=request.include_changed_files_in_predictions,
                max_depth=request.max_dependency_depth,
            )
            ranked = self.scorer.rank(candidates)[: request.top_k]
            impacted = [
                self._to_impacted_file(rank, candidate, score)
                for rank, (candidate, score) in enumerate(ranked, start=1)
            ]
            recommendations = self._recommend_tests(
                changed_files=changed_files,
                impacted_files=impacted,
                code_files=code_files,
                edges=edges,
            )
            self._attach_tests_to_impacted(impacted, recommendations)
            risk_summary = self._risk_summary(candidates)

            for impacted_file in impacted:
                code_file = next(
                    item for item in code_files if item.path == impacted_file.path
                )
                db.add(
                    ImpactPrediction(
                        analysis_run_id=analysis_run.id,
                        file_id=code_file.id,
                        path=impacted_file.path,
                        rank=impacted_file.rank,
                        score=impacted_file.score,
                        dependency_score=impacted_file.component_scores["dependency"],
                        semantic_score=impacted_file.component_scores["semantic"],
                        cochange_score=impacted_file.component_scores["cochange"],
                        test_score=impacted_file.component_scores["test"],
                        risk_score=impacted_file.component_scores["risk"],
                        reasons=[reason.model_dump() for reason in impacted_file.reasons],
                        recommended_tests=[
                            test.model_dump()
                            for test in impacted_file.recommended_tests
                        ],
                    )
                )

            analysis_run.status = "completed"
            analysis_run.changed_symbols = [
                item.model_dump() for item in changed_symbols
            ]
            analysis_run.finished_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(analysis_run)

            explanation = None
            if request.include_explanation:
                explanation = await self.explanation_service.explain_impact_prediction(
                    changed_files,
                    changed_symbols,
                    impacted,
                    recommendations,
                )

            return ImpactAnalyzeResponse(
                analysis_run_id=analysis_run.id,
                repository_id=request.repository_id,
                base_ref=request.base_ref,
                head_ref=request.head_ref,
                changed_files=changed_files,
                changed_symbols=changed_symbols,
                impacted_files=impacted,
                recommended_tests=recommendations,
                risk_summary=risk_summary,
                llm_explanation=explanation,
            )
        except Exception as exc:
            await db.rollback()
            analysis_run.status = "failed"
            analysis_run.error_message = str(exc)
            analysis_run.finished_at = datetime.now(timezone.utc)
            db.add(analysis_run)
            await db.commit()
            raise

    async def get_run(
        self, db: AsyncSession, analysis_run_id: int
    ) -> ImpactRunResponse:
        run = await db.get(AnalysisRun, analysis_run_id)
        if run is None:
            raise RepositoryNotFoundError(
                f"Analysis run with id={analysis_run_id} does not exist"
            )
        result = await db.execute(
            select(ImpactPrediction)
            .where(ImpactPrediction.analysis_run_id == analysis_run_id)
            .order_by(ImpactPrediction.rank)
        )
        predictions = [
            ImpactedFileOut(
                rank=item.rank,
                path=item.path,
                score=float(item.score),
                component_scores={
                    "dependency": float(item.dependency_score),
                    "semantic": float(item.semantic_score),
                    "cochange": float(item.cochange_score),
                    "test": float(item.test_score),
                    "risk": float(item.risk_score),
                },
                reasons=[ImpactReasonOut(**reason) for reason in (item.reasons or [])],
                recommended_tests=[
                    TestRecommendationOut(**test)
                    for test in (item.recommended_tests or [])
                ],
            )
            for item in result.scalars().all()
        ]
        return ImpactRunResponse(
            analysis_run_id=run.id,
            repository_id=run.repository_id,
            status=run.status,
            input_mode=run.input_mode,
            changed_files=run.changed_files or [],
            changed_symbols=run.changed_symbols or [],
            predictions=predictions,
        )

    async def _resolve_changed_files(
        self,
        db: AsyncSession,
        repo_obj: Repository,
        request: ImpactAnalyzeRequest,
    ) -> list[ChangedFileInput]:
        if request.changed_files:
            return request.changed_files
        if request.raw_diff:
            return [
                self._changed_file_to_input(item)
                for item in self.diff_parser.parse(request.raw_diff)
            ]
        if request.base_ref and request.head_ref:
            if not repo_obj.local_path:
                raise GitOperationError("Repository has no local path for git diff.")
            git_repo = self.git_service.open_repository(repo_obj.local_path)
            changed = self.git_service.get_changed_files_between_refs(
                git_repo, request.base_ref, request.head_ref
            )
            raw_diff = self.git_service.get_diff_between_refs(
                git_repo, request.base_ref, request.head_ref
            )
            line_ranges = {
                item.path: item.changed_lines for item in self.diff_parser.parse(raw_diff)
            }
            return [
                ChangedFileInput(
                    path=item["path"],
                    change_type=item.get("change_type", "modified"),
                    old_path=item.get("old_path"),
                    changed_lines=line_ranges.get(item["path"], []),
                )
                for item in changed
                if item.get("path")
            ]
        raise ValueError(
            "Provide base_ref/head_ref, raw_diff, or changed_files for impact analysis."
        )

    def _input_mode(self, request: ImpactAnalyzeRequest) -> str:
        if request.raw_diff:
            return "raw_diff"
        if request.changed_files:
            return "changed_files"
        return "git_diff"

    async def _load_indexed_data(
        self, db: AsyncSession, repository_id: UUID | Any
    ) -> tuple[list[CodeFile], list[Symbol], list[DependencyEdge], list[Commit]]:
        repo_obj = await self._get_repository_or_raise(db, repository_id)
        commits = (
            await db.execute(select(Commit).where(Commit.repository_id == repository_id))
        ).scalars().all()
        if repo_obj.active_generation_id is None:
            return [], [], [], list(commits)

        code_files = (
            await db.execute(
                select(CodeFile).where(
                    CodeFile.repository_id == repository_id,
                    CodeFile.generation_id == repo_obj.active_generation_id,
                )
            )
        ).scalars().all()
        symbols = (
            await db.execute(
                select(Symbol).where(
                    Symbol.repository_id == repository_id,
                    Symbol.generation_id == repo_obj.active_generation_id,
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
        return list(code_files), list(symbols), list(edges), list(commits)

    async def _score_candidates(
        self,
        db: AsyncSession,
        repository_id: UUID | Any,
        changed_files: list[ChangedFileInput],
        changed_symbols: list[ChangedSymbolOut],
        code_files: list[CodeFile],
        edges: list[DependencyEdge],
        commits: list[Commit],
        include_changed: bool,
        max_depth: int,
    ) -> list[CandidateScore]:
        changed_paths = {item.path for item in changed_files}
        candidates = {
            code_file.path: CandidateScore(path=code_file.path)
            for code_file in code_files
            if include_changed or code_file.path not in changed_paths
        }
        files_by_id = {code_file.id: code_file for code_file in code_files}
        files_by_path = {code_file.path: code_file for code_file in code_files}
        adjacency = self._reverse_adjacency(edges, files_by_id)

        for changed_path in changed_paths:
            for path, distance in self._reverse_dependents(
                changed_path, adjacency, max_depth
            ).items():
                if path not in candidates:
                    continue
                score = self.scorer.dependency_score(distance)
                candidate = candidates[path]
                candidate.dependency_score = max(candidate.dependency_score, score)
                candidate.reasons.append(
                    ImpactReason(
                        type="dependency",
                        message=f"Depends on changed file {changed_path}",
                        confidence=score,
                        evidence={"distance": distance, "changed_path": changed_path},
                    )
                )

        await self._apply_semantic_scores(
            db, repository_id, changed_files, changed_symbols, candidates
        )
        self._apply_cochange_scores(changed_paths, commits, candidates)
        self._apply_test_scores(changed_paths, code_files, edges, candidates)
        self._apply_risk_scores(code_files, edges, commits, candidates, files_by_path)
        return [candidate for candidate in candidates.values() if candidate.reasons]

    async def _apply_semantic_scores(
        self,
        db: AsyncSession,
        repository_id: UUID | Any,
        changed_files: list[ChangedFileInput],
        changed_symbols: list[ChangedSymbolOut],
        candidates: dict[str, CandidateScore],
    ) -> None:
        query = "\n".join(
            [
                "Changed files:",
                *[item.path for item in changed_files],
                "Changed symbols:",
                *[item.qualified_name for item in changed_symbols],
            ]
        )
        try:
            response = await self.semantic_search_service.semantic_search(
                db, repository_id, query, top_k=50
            )
        except Exception:
            return
        for result in response.results:
            candidate = candidates.get(result.path)
            if candidate is None:
                continue
            candidate.semantic_score = max(candidate.semantic_score, result.score)
            candidate.reasons.append(
                ImpactReason(
                    type="semantic",
                    message="Semantically similar to the change context",
                    confidence=result.score,
                    evidence={
                        "symbol": result.symbol,
                        "start_line": result.start_line,
                        "end_line": result.end_line,
                    },
                )
            )

    def _apply_cochange_scores(
        self,
        changed_paths: set[str],
        commits: list[Commit],
        candidates: dict[str, CandidateScore],
    ) -> None:
        for path, score in self.cochange_miner.score_candidates(
            changed_paths, commits
        ).items():
            candidate = candidates.get(path)
            if candidate is None:
                continue
            candidate.cochange_score = max(candidate.cochange_score, score)
            candidate.reasons.append(
                ImpactReason(
                    type="cochange",
                    message="Historically changed with an input file",
                    confidence=score,
                    evidence={"changed_paths": sorted(changed_paths)},
                )
            )

    def _apply_test_scores(
        self,
        changed_paths: set[str],
        code_files: list[CodeFile],
        edges: list[DependencyEdge],
        candidates: dict[str, CandidateScore],
    ) -> None:
        tests = self.test_service.recommend_tests(
            changed_paths=changed_paths,
            impacted_paths=set(candidates),
            code_files=code_files,
            dependency_edges=edges,
            top_k=100,
        )
        for test in tests:
            candidate = candidates.get(test.path)
            if candidate is None:
                continue
            candidate.test_score = max(candidate.test_score, test.score)
            candidate.reasons.append(
                ImpactReason(
                    type="test",
                    message=test.reason or "Related test file",
                    confidence=test.score,
                    evidence={"linked_files": test.linked_files},
                )
            )

    def _apply_risk_scores(
        self,
        code_files: list[CodeFile],
        edges: list[DependencyEdge],
        commits: list[Commit],
        candidates: dict[str, CandidateScore],
        files_by_path: dict[str, CodeFile],
    ) -> None:
        fan_in, fan_out = self._fan_counts(edges)
        churn = self._churn_counts(commits)
        for path, candidate in candidates.items():
            code_file = files_by_path.get(path)
            if code_file is None:
                continue
            risk = self.risk_service.score_file(
                code_file,
                fan_in=fan_in.get(code_file.id, 0),
                fan_out=fan_out.get(code_file.id, 0),
                churn=churn.get(path, 0),
                bugfix_churn=self.risk_service.bugfix_churn_for_file(path, commits),
            )
            candidate.risk_score = risk.score
            if candidate.reasons or risk.score >= 0.5:
                candidate.reasons.append(
                    ImpactReason(
                        type="risk",
                        message=", ".join(risk.reasons) or "Heuristic risk signal",
                        confidence=risk.score,
                        evidence=risk.components,
                    )
                )

    def _map_changed_symbols(
        self,
        changed_files: list[ChangedFileInput],
        symbols: list[Symbol],
        files_by_id: dict[int, CodeFile],
    ) -> list[ChangedSymbolOut]:
        changed_by_path = {item.path: item.changed_lines for item in changed_files}
        mapped: list[ChangedSymbolOut] = []
        for symbol in symbols:
            code_file = files_by_id.get(symbol.file_id)
            if code_file is None:
                continue
            ranges = changed_by_path.get(code_file.path)
            if ranges is None:
                continue
            if not ranges or any(
                self._ranges_overlap(
                    symbol.start_line,
                    symbol.end_line,
                    start,
                    end,
                )
                for start, end in ranges
            ):
                mapped.append(
                    ChangedSymbolOut(
                        path=code_file.path,
                        qualified_name=symbol.qualified_name,
                        symbol_type=symbol.symbol_type,
                        start_line=symbol.start_line,
                        end_line=symbol.end_line,
                    )
                )
        return mapped

    def _recommend_tests(
        self,
        changed_files: list[ChangedFileInput],
        impacted_files: list[ImpactedFileOut],
        code_files: list[CodeFile],
        edges: list[DependencyEdge],
    ) -> list[TestRecommendationOut]:
        recommendations = self.test_service.recommend_tests(
            changed_paths={item.path for item in changed_files},
            impacted_paths={item.path for item in impacted_files},
            code_files=code_files,
            dependency_edges=edges,
            top_k=20,
        )
        return [
            TestRecommendationOut(
                path=item.path,
                score=item.score,
                reason=item.reason,
                linked_files=item.linked_files,
            )
            for item in recommendations
        ]

    def _attach_tests_to_impacted(
        self,
        impacted_files: list[ImpactedFileOut],
        recommendations: list[TestRecommendationOut],
    ) -> None:
        for impacted in impacted_files:
            impacted.recommended_tests = [
                test for test in recommendations if impacted.path in test.linked_files
            ][:5]

    def _risk_summary(self, candidates: list[CandidateScore]) -> RiskSummaryOut:
        risky = sorted(
            candidates,
            key=lambda item: (-item.risk_score, item.path),
        )[:5]
        return RiskSummaryOut(
            highest_risk_files=[
                {"path": item.path, "risk_score": item.risk_score}
                for item in risky
                if item.risk_score > 0
            ]
        )

    def _to_impacted_file(
        self, rank: int, candidate: CandidateScore, score: float
    ) -> ImpactedFileOut:
        return ImpactedFileOut(
            rank=rank,
            path=candidate.path,
            score=score,
            component_scores=candidate.component_scores,
            reasons=[
                ImpactReasonOut(
                    type=reason.type,
                    message=reason.message,
                    confidence=reason.confidence,
                    evidence=reason.evidence,
                )
                for reason in candidate.reasons
            ],
        )

    def _reverse_adjacency(
        self,
        edges: list[DependencyEdge],
        files_by_id: dict[int, CodeFile],
    ) -> dict[str, set[str]]:
        adjacency: dict[str, set[str]] = {}
        for edge in edges:
            source = files_by_id.get(edge.source_file_id)
            target = files_by_id.get(edge.target_file_id)
            if source is None or target is None:
                continue
            adjacency.setdefault(target.path, set()).add(source.path)
        return adjacency

    def _reverse_dependents(
        self,
        changed_path: str,
        adjacency: dict[str, set[str]],
        max_depth: int,
    ) -> dict[str, int]:
        distances: dict[str, int] = {}
        frontier = {changed_path}
        for depth in range(1, max_depth + 1):
            next_frontier: set[str] = set()
            for path in frontier:
                for dependent in adjacency.get(path, set()):
                    if dependent in distances:
                        continue
                    distances[dependent] = depth
                    next_frontier.add(dependent)
            frontier = next_frontier
        return distances

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

    def _ranges_overlap(
        self, first_start: int, first_end: int, second_start: int, second_end: int
    ) -> bool:
        return first_start <= second_end and second_start <= first_end

    def _changed_file_to_input(self, changed_file: ChangedFile) -> ChangedFileInput:
        return ChangedFileInput(
            path=changed_file.path,
            change_type=changed_file.change_type,
            changed_lines=changed_file.changed_lines,
            old_path=changed_file.old_path,
        )

    async def _get_repository_or_raise(
        self, db: AsyncSession, repository_id: UUID | Any
    ) -> Repository:
        repo_obj = await db.get(Repository, repository_id)
        if repo_obj is None:
            raise RepositoryNotFoundError(
                f"Repository with id={repository_id} does not exist"
            )
        return repo_obj
