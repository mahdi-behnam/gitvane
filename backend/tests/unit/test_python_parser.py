from app.analysis.languages import Language
from app.analysis.python_parser import PythonParser


def test_python_parser_extracts_imports_symbols_and_calls() -> None:
    source = '''
import os
import pathlib as pl
from .auth import token as token_mod
from package.module import helper, Thing

class Base:
    pass

@decorator
class TestService(Base):
    """service docs"""

    async def fetch(self, value: str) -> int:
        helper(value)
        return len(value)

def build(x: int) -> str:
    return token_mod.issue(str(x))
'''

    parsed = PythonParser().parse("src/service.py", source)

    assert parsed.language == Language.PYTHON
    assert parsed.errors == []
    assert {item.module for item in parsed.imports} >= {
        "os",
        "pathlib",
        "auth",
        "package.module",
    }
    relative = next(item for item in parsed.imports if item.module == "auth")
    assert relative.level == 1
    assert relative.names == ["token"]
    assert relative.alias == "token_mod"

    symbols = {symbol.qualified_name: symbol for symbol in parsed.symbols}
    assert symbols["TestService"].symbol_type == "class"
    assert symbols["TestService"].bases == ["Base"]
    assert symbols["TestService"].decorators == ["decorator"]
    assert symbols["TestService"].is_test is True
    assert symbols["TestService.fetch"].symbol_type == "method"
    assert symbols["TestService.fetch"].metadata["async"] is True
    assert symbols["build"].signature == "def build(x: int) -> str"

    assert {call.name for call in parsed.calls} >= {
        "helper",
        "len",
        "token_mod.issue",
        "str",
    }
    assert {export.name for export in parsed.exports} >= {"TestService", "build"}


def test_python_parser_reads_explicit_all_exports() -> None:
    source = '''
__all__ = ["public"]

def public():
    pass

def other():
    pass
'''

    parsed = PythonParser().parse("pkg/mod.py", source)

    assert [export.name for export in parsed.exports] == ["public"]


def test_python_parser_reports_syntax_errors_without_raising() -> None:
    parsed = PythonParser().parse("broken.py", "def nope(:\n")

    assert parsed.symbols == []
    assert len(parsed.errors) == 1
    assert "invalid syntax" in parsed.errors[0].message
