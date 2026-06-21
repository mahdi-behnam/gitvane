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
