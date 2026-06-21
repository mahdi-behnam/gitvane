from dataclasses import dataclass, field

from app.core.config import settings


@dataclass(frozen=True)
class ImpactReason:
    type: str
    message: str
    confidence: float
    evidence: dict[str, object] = field(default_factory=dict)


@dataclass
class CandidateScore:
    path: str
    dependency_score: float = 0.0
    semantic_score: float = 0.0
    cochange_score: float = 0.0
    test_score: float = 0.0
    risk_score: float = 0.0
    reasons: list[ImpactReason] = field(default_factory=list)

    @property
    def component_scores(self) -> dict[str, float]:
        return {
            "dependency": self.dependency_score,
            "semantic": self.semantic_score,
            "cochange": self.cochange_score,
            "test": self.test_score,
            "risk": self.risk_score,
        }


class ImpactScorer:
    """Combine deterministic component scores into a ranked result."""

    def __init__(
        self,
        dependency_weight: float | None = None,
        semantic_weight: float | None = None,
        cochange_weight: float | None = None,
        test_weight: float | None = None,
        risk_weight: float | None = None,
    ) -> None:
        self.weights = {
            "dependency": dependency_weight
            if dependency_weight is not None
            else settings.IMPACT_DEPENDENCY_WEIGHT,
            "semantic": semantic_weight
            if semantic_weight is not None
            else settings.IMPACT_SEMANTIC_WEIGHT,
            "cochange": cochange_weight
            if cochange_weight is not None
            else settings.IMPACT_COCHANGE_WEIGHT,
            "test": test_weight if test_weight is not None else settings.IMPACT_TEST_WEIGHT,
            "risk": risk_weight if risk_weight is not None else settings.IMPACT_RISK_WEIGHT,
        }

    def final_score(self, candidate: CandidateScore) -> float:
        score = (
            self.weights["dependency"] * self.cap(candidate.dependency_score)
            + self.weights["semantic"] * self.cap(candidate.semantic_score)
            + self.weights["cochange"] * self.cap(candidate.cochange_score)
            + self.weights["test"] * self.cap(candidate.test_score)
            + self.weights["risk"] * self.cap(candidate.risk_score)
        )
        return round(self.cap(score), 4)

    def dependency_score(self, distance: int, path_count: int = 1) -> float:
        base = {1: 1.0, 2: 0.65, 3: 0.40}.get(distance, 0.20)
        bonus = min(max(path_count - 1, 0) * 0.08, 0.20)
        return self.cap(base + bonus)

    def rank(self, candidates: list[CandidateScore]) -> list[tuple[CandidateScore, float]]:
        return sorted(
            ((candidate, self.final_score(candidate)) for candidate in candidates),
            key=lambda item: (-item[1], item[0].path),
        )

    def cap(self, value: float) -> float:
        return max(0.0, min(float(value), 1.0))
