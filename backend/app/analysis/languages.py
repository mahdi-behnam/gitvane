from enum import Enum
from pathlib import Path


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    UNKNOWN = "unknown"


def detect_language_from_path(file_path: str | Path) -> Language:
    """Detects programming language from extension"""
    ext = Path(file_path).suffix.lower()
    if ext == ".py":
        return Language.PYTHON
    elif ext in (".js", ".jsx"):
        return Language.JAVASCRIPT
    elif ext in (".ts", ".tsx"):
        return Language.TYPESCRIPT
    return Language.UNKNOWN
