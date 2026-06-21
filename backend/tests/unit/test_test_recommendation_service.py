from app.db.models import CodeFile, DependencyEdge
from app.services.test_recommendation_service import TestRecommendationService


def test_recommends_tests_by_import_edge() -> None:
    source = CodeFile(
        id=1,
        repository_id=1,
        path="src/auth/token.py",
        language="python",
        content_hash="a",
        is_test=False,
    )
    test = CodeFile(
        id=2,
        repository_id=1,
        path="tests/test_token.py",
        language="python",
        content_hash="b",
        is_test=True,
    )
    edge = DependencyEdge(
        repository_id=1,
        source_file_id=2,
        target_file_id=1,
        edge_type="test_import",
    )

    recommendations = TestRecommendationService().recommend_tests(
        changed_paths={"src/auth/token.py"},
        impacted_paths=set(),
        code_files=[source, test],
        dependency_edges=[edge],
    )

    assert recommendations[0].path == "tests/test_token.py"
    assert recommendations[0].score == 0.95
    assert recommendations[0].linked_files == ["src/auth/token.py"]


def test_recommends_tests_by_naming_convention() -> None:
    source = CodeFile(
        id=1,
        repository_id=1,
        path="src/auth/token.ts",
        language="typescript",
        content_hash="a",
        is_test=False,
    )
    test = CodeFile(
        id=2,
        repository_id=1,
        path="src/auth/token.test.ts",
        language="typescript",
        content_hash="b",
        is_test=True,
    )

    recommendations = TestRecommendationService().recommend_tests(
        changed_paths={"src/auth/token.ts"},
        impacted_paths=set(),
        code_files=[source, test],
        dependency_edges=[],
    )

    assert recommendations[0].path == "src/auth/token.test.ts"
    assert recommendations[0].score == 0.85
