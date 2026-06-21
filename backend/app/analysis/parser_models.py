from dataclasses import dataclass, field
from typing import Any

from app.analysis.languages import Language


@dataclass(frozen=True)
class ParsedImport:
    module: str | None
    names: list[str] = field(default_factory=list)
    alias: str | None = None
    level: int = 0
    line: int = 0
    import_type: str = "import"
    confidence: float = 1.0


@dataclass(frozen=True)
class ParsedExport:
    name: str
    line: int = 0
    export_type: str = "export"
    confidence: float = 1.0


@dataclass(frozen=True)
class ParsedSymbol:
    qualified_name: str
    simple_name: str
    symbol_type: str
    start_line: int
    end_line: int
    signature: str | None = None
    docstring: str | None = None
    decorators: list[str] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)
    is_test: bool = False
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedCall:
    name: str
    line: int
    caller: str | None = None
    confidence: float = 0.8


@dataclass(frozen=True)
class ParsedError:
    message: str
    line: int | None = None
    column: int | None = None


@dataclass(frozen=True)
class ParsedFile:
    path: str
    language: Language
    imports: list[ParsedImport] = field(default_factory=list)
    exports: list[ParsedExport] = field(default_factory=list)
    symbols: list[ParsedSymbol] = field(default_factory=list)
    calls: list[ParsedCall] = field(default_factory=list)
    errors: list[ParsedError] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
