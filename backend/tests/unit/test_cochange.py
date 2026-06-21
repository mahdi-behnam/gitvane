from types import SimpleNamespace

from app.analysis.cochange import CochangeMiner


def test_cochange_score_normalizes_joint_changes() -> None:
    commits = [
        SimpleNamespace(
            sha="1",
            changed_files=[{"path": "a.py"}, {"path": "b.py"}],
        ),
        SimpleNamespace(
            sha="2",
            changed_files=[{"path": "a.py"}, {"path": "b.py"}],
        ),
        SimpleNamespace(
            sha="3",
            changed_files=[{"path": "b.py"}],
        ),
    ]

    scores = CochangeMiner().score_candidates({"a.py"}, commits)

    assert round(scores["b.py"], 4) == 0.8165


def test_cochange_score_handles_empty_history() -> None:
    assert CochangeMiner().score_candidates({"a.py"}, []) == {}
