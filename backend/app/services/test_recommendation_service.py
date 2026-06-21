from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from app.db.models import CodeFile, DependencyEdge


@dataclass(frozen=True)
class TestRecommendation:
    path: str
    score: float
    reason: str
    linked_files: list[str] = field(default_factory=list)


class TestRecommendationService:
    """Recommend tests from indexed files without executing them."""

    def recommend_tests(
        self,
        changed_paths: set[str],
        impacted_paths: set[str],
        code_files: list[CodeFile],
        dependency_edges: list[DependencyEdge],
        commits: list[Any] | None = None,
        semantic_scores: dict[str, float] | None = None,
        top_k: int = 10,
    ) -> list[TestRecommendation]:
        source_paths = changed_paths | impacted_paths
        files_by_id = {code_file.id: code_file for code_file in code_files}
        semantic_scores = semantic_scores or {}
        commits = commits or []
        scores: dict[str, TestRecommendation] = {}

        for code_file in code_files:
            if not code_file.is_test:
                continue
            linked: set[str] = set()
            score = 0.0
            reasons: list[str] = []

            for source_path in source_paths:
                naming_score = self._naming_score(source_path, code_file.path)
                if naming_score:
                    score = max(score, naming_score)
                    linked.add(source_path)
                    reasons.append("Matches source/test naming convention")

                proximity_score = self._directory_proximity_score(
                    source_path, code_file.path
                )
                if proximity_score:
                    score = max(score, proximity_score)
                    linked.add(source_path)
                    reasons.append("Near changed or impacted file")

                cochange_score = self._cochange_score(
                    source_path, code_file.path, commits
                )
                if cochange_score:
                    score = max(score, cochange_score)
                    linked.add(source_path)
                    reasons.append("Historically changed with source file")

            for edge in dependency_edges:
                source = files_by_id.get(edge.source_file_id)
                target = files_by_id.get(edge.target_file_id)
                if source is None or target is None:
                    continue
                if source.path == code_file.path and target.path in source_paths:
                    score = max(score, 0.95)
                    linked.add(target.path)
                    reasons.append("Imports changed or impacted file")

            semantic_score = semantic_scores.get(code_file.path, 0.0)
            if semantic_score:
                score = max(score, min(semantic_score, 0.8))
                reasons.append("Semantically similar to change context")

            if score > 0:
                scores[code_file.path] = TestRecommendation(
                    path=code_file.path,
                    score=round(min(score, 1.0), 4),
                    reason="; ".join(dict.fromkeys(reasons)),
                    linked_files=sorted(linked),
                )

        return sorted(scores.values(), key=lambda item: (-item.score, item.path))[:top_k]

    def _naming_score(self, source_path: str, test_path: str) -> float:
        source = PurePosixPath(source_path)
        test = PurePosixPath(test_path)
        source_stem = source.stem
        test_name = test.name
        if test_name in {f"test_{source_stem}.py", f"{source_stem}_test.py"}:
            return 0.85
        if test_name in {
            f"{source_stem}.test.ts",
            f"{source_stem}.spec.ts",
            f"{source_stem}.test.js",
            f"{source_stem}.spec.js",
        }:
            return 0.85
        if "tests" in test.parts and source_stem in test.stem:
            return 0.65
        return 0.0

    def _directory_proximity_score(self, source_path: str, test_path: str) -> float:
        source = PurePosixPath(source_path)
        test = PurePosixPath(test_path)
        if source.parent == test.parent:
            return 0.55
        if "tests" in test.parts and source.parent.name in test.parts:
            return 0.50
        if source.parent.name and source.parent.name in test.parts:
            return 0.45
        return 0.0

    def _cochange_score(
        self,
        source_path: str,
        test_path: str,
        commits: list[Any],
    ) -> float:
        source_count = 0
        test_count = 0
        joint_count = 0
        for commit in commits:
            paths = self._commit_paths(commit)
            if source_path in paths:
                source_count += 1
            if test_path in paths:
                test_count += 1
            if source_path in paths and test_path in paths:
                joint_count += 1
        if not source_count or not test_count or not joint_count:
            return 0.0
        return min(joint_count / ((source_count * test_count) ** 0.5), 0.75)

    def _commit_paths(self, commit: Any) -> set[str]:
        changed_files = getattr(commit, "changed_files", None)
        if changed_files is None and isinstance(commit, dict):
            changed_files = commit.get("changed_files")
        paths: set[str] = set()
        for item in changed_files or []:
            if isinstance(item, str):
                paths.add(item)
            elif isinstance(item, dict) and item.get("path"):
                paths.add(str(item["path"]))
        return paths
