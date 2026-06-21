from dataclasses import dataclass, field

from app.db.models import CodeFile


@dataclass(frozen=True)
class FileRisk:
    path: str
    score: float
    components: dict[str, float]
    reasons: list[str] = field(default_factory=list)


class RiskService:
    """Compute heuristic file risk from indexed metadata."""

    BUGFIX_KEYWORDS = ("fix", "bug", "regression", "hotfix", "patch", "broken")

    def score_file(
        self,
        code_file: CodeFile,
        fan_in: int = 0,
        fan_out: int = 0,
        churn: int = 0,
        bugfix_churn: int = 0,
    ) -> FileRisk:
        loc = int(code_file.loc or 0)
        components = {
            "fan_in": self._scale(fan_in, 10),
            "fan_out": self._scale(fan_out, 10),
            "churn": self._scale(churn, 20),
            "file_size": self._scale(loc, 500),
            "bugfix_frequency": self._scale(bugfix_churn, 8),
            "test_coverage_proxy": 0.2 if not code_file.is_test else 0.0,
        }
        score = round(
            min(
                1.0,
                components["fan_in"] * 0.25
                + components["fan_out"] * 0.15
                + components["churn"] * 0.25
                + components["file_size"] * 0.15
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
            "churn": "Frequently changed",
            "file_size": "Large file",
            "bugfix_frequency": "Often touched by bugfix commits",
            "test_coverage_proxy": "Weak test proximity signal",
        }
        return [label for key, label in labels.items() if components.get(key, 0.0) >= 0.5]
