import ast
from pathlib import Path
from typing import Iterable

from app.analysis.languages import Language
from app.analysis.parser_models import (
    ParsedCall,
    ParsedError,
    ParsedExport,
    ParsedFile,
    ParsedImport,
    ParsedSymbol,
)


class PythonParser:
    """Parse Python source with ast and return best-effort static metadata."""

    def parse(self, path: str | Path, content: str | bytes) -> ParsedFile:
        source = self._decode_content(content)
        file_path = str(path)
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError as exc:
            return ParsedFile(
                path=file_path,
                language=Language.PYTHON,
                errors=[
                    ParsedError(
                        message=exc.msg,
                        line=exc.lineno,
                        column=exc.offset,
                    )
                ],
            )
        except Exception as exc:
            return ParsedFile(
                path=file_path,
                language=Language.PYTHON,
                errors=[ParsedError(message=str(exc))],
            )

        visitor = _PythonVisitor(source)
        visitor.visit(tree)
        exports = visitor.exports or self._exports_from_symbols(visitor.symbols)
        return ParsedFile(
            path=file_path,
            language=Language.PYTHON,
            imports=visitor.imports,
            exports=exports,
            symbols=visitor.symbols,
            calls=visitor.calls,
            errors=[],
        )

    def _decode_content(self, content: str | bytes) -> str:
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="replace")
        return content

    def _exports_from_symbols(
        self, symbols: Iterable[ParsedSymbol]
    ) -> list[ParsedExport]:
        return [
            ParsedExport(
                name=symbol.simple_name,
                line=symbol.start_line,
                export_type=symbol.symbol_type,
            )
            for symbol in symbols
            if "." not in symbol.qualified_name
            and symbol.symbol_type in {"class", "function"}
            and not symbol.simple_name.startswith("_")
        ]


class _PythonVisitor(ast.NodeVisitor):
    def __init__(self, source: str) -> None:
        self.source = source
        self.imports: list[ParsedImport] = []
        self.exports: list[ParsedExport] = []
        self.symbols: list[ParsedSymbol] = []
        self.calls: list[ParsedCall] = []
        self._scope: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(
                ParsedImport(
                    module=alias.name,
                    names=[],
                    alias=alias.asname,
                    line=node.lineno,
                    import_type="import",
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.imports.append(
            ParsedImport(
                module=node.module,
                names=[alias.name for alias in node.names],
                alias=self._single_alias(node.names),
                level=node.level,
                line=node.lineno,
                import_type="from_import",
            )
        )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualified_name = self._qualified_name(node.name)
        self.symbols.append(
            ParsedSymbol(
                qualified_name=qualified_name,
                simple_name=node.name,
                symbol_type="class",
                start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
                signature=self._class_signature(node),
                docstring=ast.get_docstring(node),
                decorators=[self._unparse(item) for item in node.decorator_list],
                bases=[self._unparse(item) for item in node.bases],
                is_test=node.name.startswith("Test"),
            )
        )
        self._scope.append(node.name)
        for child in node.body:
            self.visit(child)
        self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node, is_async=True)

    def visit_Call(self, node: ast.Call) -> None:
        self.calls.append(
            ParsedCall(
                name=self._call_name(node.func),
                line=node.lineno,
                caller=".".join(self._scope) or None,
            )
        )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if self._is_all_assignment(node):
            self.exports.extend(
                ParsedExport(name=name, line=node.lineno, export_type="explicit")
                for name in self._string_list(node.value)
            )
        self.generic_visit(node)

    def _visit_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, *, is_async: bool
    ) -> None:
        qualified_name = self._qualified_name(node.name)
        is_method = bool(self._scope)
        self.symbols.append(
            ParsedSymbol(
                qualified_name=qualified_name,
                simple_name=node.name,
                symbol_type="method" if is_method else "function",
                start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
                signature=self._function_signature(node, is_async=is_async),
                docstring=ast.get_docstring(node),
                decorators=[self._unparse(item) for item in node.decorator_list],
                is_test=node.name.startswith("test_"),
                metadata={"async": is_async},
            )
        )
        self._scope.append(node.name)
        for child in node.body:
            self.visit(child)
        self._scope.pop()

    def _qualified_name(self, name: str) -> str:
        return ".".join([*self._scope, name])

    def _function_signature(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, *, is_async: bool
    ) -> str:
        args = self._unparse(node.args)
        prefix = "async def" if is_async else "def"
        returns = f" -> {self._unparse(node.returns)}" if node.returns else ""
        return f"{prefix} {node.name}({args}){returns}"

    def _class_signature(self, node: ast.ClassDef) -> str:
        bases = ", ".join(self._unparse(base) for base in node.bases)
        return f"class {node.name}({bases})" if bases else f"class {node.name}"

    def _call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            value = self._call_name(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        return self._unparse(node)

    def _unparse(self, node: ast.AST | None) -> str:
        if node is None:
            return ""
        try:
            return ast.unparse(node)
        except Exception:
            return ""

    def _single_alias(self, aliases: list[ast.alias]) -> str | None:
        aliased = [alias.asname for alias in aliases if alias.asname]
        return aliased[0] if len(aliased) == 1 else None

    def _is_all_assignment(self, node: ast.Assign) -> bool:
        return any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )

    def _string_list(self, node: ast.AST) -> list[str]:
        if isinstance(node, (ast.List, ast.Tuple)):
            return [
                item.value
                for item in node.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            ]
        return []
