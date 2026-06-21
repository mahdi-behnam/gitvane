from app.analysis.file_classifier import FileClassifier
from app.analysis.languages import Language
from app.analysis.test_detector import TestDetector


def test_file_classifier_detects_language_test_and_loc() -> None:
    classifier = FileClassifier()

    result = classifier.classify("tests/test_auth.py", "def test_login():\n    pass\n")

    assert result["language"] == Language.PYTHON
    assert result["is_supported"] is True
    assert result["is_test"] is True
    assert result["is_generated"] is False
    assert result["loc"] == 2


def test_file_classifier_detects_generated_markers() -> None:
    classifier = FileClassifier()

    result = classifier.classify(
        "src/client.ts",
        "// This file is auto-generated. Do not edit.\nexport const x = 1;\n",
    )

    assert result["is_generated"] is True


def test_test_detector_detects_js_test_conventions() -> None:
    detector = TestDetector()

    assert detector.is_test_file("src/auth/token.spec.ts") is True
    assert detector.is_test_file("src/auth/token.ts", "describe('token', () => {})")
    assert detector.is_test_file("src/auth/token.ts", "export const x = 1") is False


def test_test_detector_detects_python_test_code() -> None:
    detector = TestDetector()

    assert detector.is_test_file("src/auth/token.py", "class TestToken:\n    pass\n")
    assert detector.is_test_symbol("test_token", "function") is True
    assert detector.is_test_symbol("Token", "class") is False
