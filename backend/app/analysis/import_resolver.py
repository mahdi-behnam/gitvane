import posixpath
from pathlib import Path, PurePosixPath

from app.analysis.languages import Language, detect_language_from_path
from app.analysis.parser_models import ParsedImport


class ImportResolver:
    """Resolve parsed imports into repository-relative file paths."""

    PYTHON_SUFFIXES = (".py", "/__init__.py")
    JS_TS_SUFFIXES = (
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        "/index.ts",
        "/index.tsx",
        "/index.js",
        "/index.jsx",
    )

    def resolve_import(
        self,
        source_path: str | Path,
        parsed_import: ParsedImport,
        candidate_paths: set[str],
    ) -> str | None:
        source = PurePosixPath(Path(source_path).as_posix())
        language = detect_language_from_path(source.as_posix())
        if language is Language.PYTHON:
            return self.resolve_python_import(source, parsed_import, candidate_paths)
        if language in {Language.JAVASCRIPT, Language.TYPESCRIPT}:
            return self.resolve_js_ts_import(source, parsed_import, candidate_paths)
        return None

    def resolve_python_import(
        self,
        source_path: PurePosixPath,
        parsed_import: ParsedImport,
        candidate_paths: set[str],
    ) -> str | None:
        module_parts = (parsed_import.module or "").split(".")
        module_parts = [part for part in module_parts if part]

        if parsed_import.level > 0:
            package_dir = source_path.parent
            for _ in range(max(parsed_import.level - 1, 0)):
                package_dir = package_dir.parent
            base_parts = list(package_dir.parts) + module_parts
        else:
            base_parts = module_parts

        if not base_parts:
            return None

        resolved = self._first_existing(
            "/".join(base_parts), self.PYTHON_SUFFIXES, candidate_paths
        )
        if resolved:
            return resolved

        for imported_name in parsed_import.names:
            if imported_name == "*":
                continue
            resolved = self._first_existing(
                "/".join([*base_parts, imported_name]),
                self.PYTHON_SUFFIXES,
                candidate_paths,
            )
            if resolved:
                return resolved
        return None

    def resolve_js_ts_import(
        self,
        source_path: PurePosixPath,
        parsed_import: ParsedImport,
        candidate_paths: set[str],
    ) -> str | None:
        module = parsed_import.module or ""
        if not module.startswith((".", "/")):
            return None

        if module.startswith("/"):
            base = module.lstrip("/")
        else:
            base = (source_path.parent / module).as_posix()
        normalized = posixpath.normpath(PurePosixPath(base).as_posix())

        suffixes = self.JS_TS_SUFFIXES
        if normalized.endswith((".js", ".jsx", ".ts", ".tsx")):
            suffixes = ("",)
        return self._first_existing(normalized, suffixes, candidate_paths)

    def _first_existing(
        self,
        base: str,
        suffixes: tuple[str, ...],
        candidate_paths: set[str],
    ) -> str | None:
        normalized = posixpath.normpath(PurePosixPath(base).as_posix()).lstrip("./")
        for suffix in suffixes:
            candidate = f"{normalized}{suffix}"
            if candidate in candidate_paths:
                return candidate
        return None
