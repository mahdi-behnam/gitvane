from dataclasses import dataclass, field
from pathlib import PurePosixPath

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
        top_k: int = 10,
    ) -> list[TestRecommendation]:
        source_paths = changed_paths | impacted_paths
        files_by_id = {code_file.id: code_file for code_file in code_files}
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

            for edge in dependency_edges:
                source = files_by_id.get(edge.source_file_id)
                target = files_by_id.get(edge.target_file_id)
                if source is None or target is None:
                    continue
                if source.path == code_file.path and target.path in source_paths:
                    score = max(score, 0.95)
                    linked.add(target.path)
                    reasons.append("Imports changed or impacted file")

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
