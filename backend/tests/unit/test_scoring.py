from app.analysis.scoring import CandidateScore, ImpactReason, ImpactScorer


def test_weighted_score_is_capped_and_rounded() -> None:
    scorer = ImpactScorer(
        dependency_weight=0.5,
        semantic_weight=0.2,
        cochange_weight=0.1,
        test_weight=0.1,
        risk_weight=0.1,
    )
    candidate = CandidateScore(
        path="src/api.py",
        dependency_score=2.0,
        semantic_score=0.5,
        cochange_score=0.5,
        test_score=0.0,
        risk_score=0.5,
    )

    assert scorer.final_score(candidate) == 0.7


def test_dependency_score_decays_with_distance() -> None:
    scorer = ImpactScorer()

    assert scorer.dependency_score(distance=1) == 1.0
    assert scorer.dependency_score(distance=2) == 0.65
    assert scorer.dependency_score(distance=3) == 0.4


def test_candidate_reasons_are_preserved() -> None:
    reason = ImpactReason(
        type="dependency",
        message="Imports changed file",
        confidence=0.9,
        evidence={"distance": 1},
    )
    candidate = CandidateScore(path="src/api.py", reasons=[reason])

    assert candidate.reasons == [reason]
