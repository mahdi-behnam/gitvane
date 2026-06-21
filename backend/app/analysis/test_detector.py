import re
from pathlib import Path


class TestDetector:
    """Detect whether files and symbols are likely tests."""

    PYTHON_TEST_FUNCTION = re.compile(r"^\s*def\s+test_[\w_]+\s*\(", re.MULTILINE)
    PYTHON_TEST_CLASS = re.compile(r"^\s*class\s+Test\w*\s*[:(]", re.MULTILINE)
    JS_TEST_CALL = re.compile(r"\b(describe|it|test|expect)\s*\(")

    def is_test_file(
        self, file_path: str | Path, content: str | bytes | None = None
    ) -> bool:
        path = Path(file_path).as_posix()
        lower_path = path.lower()
        name = Path(lower_path).name
        text = self._decode_content(content)

        if "/tests/" in f"/{lower_path}" or "/__tests__/" in f"/{lower_path}":
            return True
        if name.startswith("test_") and name.endswith(".py"):
            return True
        if name.endswith("_test.py"):
            return True
        if any(
            name.endswith(suffix)
            for suffix in (".test.js", ".spec.js", ".test.ts", ".spec.ts")
        ):
            return True

        return self.contains_test_code(path, text)

    def contains_test_code(self, file_path: str | Path, content: str | bytes) -> bool:
        path = Path(file_path).as_posix().lower()
        text = self._decode_content(content)
        if path.endswith(".py"):
            return bool(
                self.PYTHON_TEST_FUNCTION.search(text)
                or self.PYTHON_TEST_CLASS.search(text)
            )
        if path.endswith((".js", ".jsx", ".ts", ".tsx")):
            return bool(self.JS_TEST_CALL.search(text))
        return False

    def is_test_symbol(self, name: str, symbol_type: str) -> bool:
        if symbol_type in {"function", "method"}:
            return name.startswith("test_") or name in {"describe", "it", "test"}
        if symbol_type == "class":
            return name.startswith("Test")
        return False

    def _decode_content(self, content: str | bytes | None) -> str:
        if content is None:
            return ""
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="replace")
        return content
