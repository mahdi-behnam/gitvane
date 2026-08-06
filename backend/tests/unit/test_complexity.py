from app.analysis.complexity import ComplexityCalculator
from app.analysis.languages import Language


def test_python_complexity_counts_branches_and_functions() -> None:
    source = """
def validate(value):
    if value:
        for item in value:
            if item:
                return True
    return False
"""

    calculator = ComplexityCalculator()

    assert calculator.branch_count(source, Language.PYTHON) == 3
    assert calculator.function_count(source, Language.PYTHON) == 1
    assert calculator.max_nesting_depth(source, Language.PYTHON) == 3
    assert calculator.score(source, Language.PYTHON) > 0


def test_javascript_complexity_counts_branch_tokens() -> None:
    source = """
export function validate(value) {
  if (value && value.ok) {
    return value.items.map((item) => item ? true : false);
  }
}
"""

    calculator = ComplexityCalculator()

    assert calculator.branch_count(source, Language.JAVASCRIPT) >= 3
    assert calculator.function_count(source, Language.JAVASCRIPT) >= 2
    assert calculator.max_nesting_depth(source, Language.JAVASCRIPT) >= 1


def test_complexity_case_insensitive_and_aliases() -> None:
    py_source = """
def process(data):
    if data:
        return len(data)
    return 0
"""
    js_source = """
function process(data) {
    if (data) {
        return data.length;
    }
    return 0;
}
"""
    calculator = ComplexityCalculator()

    for lang in ["Python", "PYTHON", "py", "PY", "Language.PYTHON"]:
        assert calculator.branch_count(py_source, lang) == 1
        assert calculator.function_count(py_source, lang) == 1
        assert calculator.max_nesting_depth(py_source, lang) == 1
        assert calculator.score(py_source, lang) > 0

    for lang in ["JavaScript", "JAVASCRIPT", "js", "JS", "Language.JAVASCRIPT"]:
        assert calculator.branch_count(js_source, lang) == 1
        assert calculator.function_count(js_source, lang) == 1
        assert calculator.max_nesting_depth(js_source, lang) == 2
        assert calculator.score(js_source, lang) > 0

    for lang in ["TypeScript", "TYPESCRIPT", "ts", "TS"]:
        assert calculator.branch_count(js_source, lang) == 1
        assert calculator.function_count(js_source, lang) == 1
        assert calculator.max_nesting_depth(js_source, lang) == 2
        assert calculator.score(js_source, lang) > 0

