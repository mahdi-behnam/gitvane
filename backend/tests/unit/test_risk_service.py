from types import SimpleNamespace

from app.db.models import CodeFile
from app.services.risk_service import RiskService


def test_risk_service_scores_file_components() -> None:
    code_file = CodeFile(
        id=1,
        repository_id=1,
        path="src/core/payment.py",
        language="python",
        content_hash="abc",
        loc=400,
        is_test=False,
    )

    risk = RiskService().score_file(
        code_file,
        fan_in=8,
        fan_out=3,
        churn=12,
        bugfix_churn=2,
    )

    assert risk.path == "src/core/payment.py"
    assert 0.0 < risk.score <= 1.0
    assert risk.components["fan_in"] == 0.8
    assert "High fan-in" in risk.reasons


def test_risk_service_counts_bugfix_churn() -> None:
    commits = [
        SimpleNamespace(
            message="Fix payment regression",
            changed_files=[{"path": "src/core/payment.py"}],
        ),
        SimpleNamespace(
            message="Refactor names",
            changed_files=[{"path": "src/core/payment.py"}],
        ),
    ]

    assert RiskService().bugfix_churn_for_file("src/core/payment.py", commits) == 1
