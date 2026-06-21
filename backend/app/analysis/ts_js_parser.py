import re
from pathlib import Path
from typing import Callable

import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language as TreeSitterLanguage
from tree_sitter import Node, Parser

from app.analysis.languages import Language, detect_language_from_path
from app.analysis.parser_models import (
    ParsedCall,
    ParsedError,
    ParsedExport,
    ParsedFile,
    ParsedImport,
    ParsedSymbol,
)


class TsJsParser:
    """Parse JavaScript and TypeScript with tree-sitter."""

    def parse(self, path: str | Path, content: str | bytes) -> ParsedFile:
        file_path = str(path)
        language = detect_language_from_path(file_path)
        source = self._decode_content(content)
        try:
            parser = self._parser_for_path(file_path)
            tree = parser.parse(source.encode("utf-8"))
            collector = _TsJsCollector(file_path, source, language)
            collector.visit(tree.root_node)
            errors = collector.errors
            if tree.root_node.has_error:
                errors.append(
                    ParsedError(
                        message="tree-sitter reported syntax errors",
                        line=tree.root_node.start_point[0] + 1,
                        column=tree.root_node.start_point[1],
                    )
                )
            return ParsedFile(
                path=file_path,
                language=language,
                imports=collector.imports,
                exports=collector.exports,
                symbols=collector.symbols,
                calls=collector.calls,
                errors=errors,
                metadata={"parser": "tree-sitter"},
            )
        except Exception as exc:
            return ParsedFile(
                path=file_path,
                language=language,
                errors=[ParsedError(message=str(exc))],
                metadata={"parser": "tree-sitter"},
            )

    def _decode_content(self, content: str | bytes) -> str:
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="replace")
        return content

    def _parser_for_path(self, path: str) -> Parser:
        parser = Parser()
        if Path(path).suffix.lower() == ".tsx":
            parser.language = TreeSitterLanguage(
                tree_sitter_typescript.language_tsx()
            )
        elif detect_language_from_path(path) == Language.TYPESCRIPT:
            parser.language = TreeSitterLanguage(
                tree_sitter_typescript.language_typescript()
            )
        else:
            parser.language = TreeSitterLanguage(tree_sitter_javascript.language())
        return parser


class _TsJsCollector:
    def __init__(self, path: str, source: str, language: Language) -> None:
        self.path = path
        self.source = source
        self.language = language
        self.imports: list[ParsedImport] = []
        self.exports: list[ParsedExport] = []
        self.symbols: list[ParsedSymbol] = []
        self.calls: list[ParsedCall] = []
        self.errors: list[ParsedError] = []
        self._class_stack: list[str] = []
        self._seen_symbols: set[tuple[str, int]] = set()

    def visit(self, node: Node) -> None:
        handler = getattr(self, f"_visit_{node.type}", None)
        if handler:
            should_skip_children = handler(node)
            if should_skip_children:
                return
        for child in node.children:
            self.visit(child)

    def _visit_import_statement(self, node: Node) -> bool:
        text = self._text(node)
        module = self._quoted_module(text)
        names = self._import_names(text)
        if module:
            self.imports.append(
                ParsedImport(
                    module=module,
                    names=names,
                    alias=self._default_import_name(text),
                    line=self._line(node),
                    import_type="es_import",
                )
            )
        return False

    def _visit_export_statement(self, node: Node) -> bool:
        text = self._text(node)
        line = self._line(node)
        for name in self._export_names(text):
            self.exports.append(ParsedExport(name=name, line=line))
        return False

    def _visit_lexical_declaration(self, node: Node) -> bool:
        text = self._text(node)
        require_match = re.search(
            r"\b(?:const|let|var)\s+([\w$]+)\s*=\s*require\((['\"])(.+?)\2\)",
            text,
        )
        if require_match:
            self.imports.append(
                ParsedImport(
                    module=require_match.group(3),
                    names=[],
                    alias=require_match.group(1),
                    line=self._line(node),
                    import_type="require",
                )
            )

        arrow_match = re.search(
            r"\b(?:const|let|var)\s+([\w$]+)\s*=\s*(?:async\s*)?\(?[^=]*?\)?\s*=>",
            text,
            re.DOTALL,
        )
        function_match = re.search(
            r"\b(?:const|let|var)\s+([\w$]+)\s*=\s*(?:async\s*)?function\b",
            text,
        )
        match = arrow_match or function_match
        if match:
            self._add_symbol(
                name=match.group(1),
                symbol_type="function",
                node=node,
                signature=self._first_line(text),
                metadata={"assignment": True},
            )
        return False

    def _visit_variable_declaration(self, node: Node) -> bool:
        return self._visit_lexical_declaration(node)

    def _visit_function_declaration(self, node: Node) -> bool:
        name = self._child_name(node, {"identifier", "property_identifier"})
        if name:
            self._add_symbol(
                name=name,
                symbol_type="function",
                node=node,
                signature=self._signature_until_body(node),
            )
        return False

    def _visit_class_declaration(self, node: Node) -> bool:
        name = self._child_name(node, {"type_identifier", "identifier"})
        if name:
            self._add_symbol(
                name=name,
                symbol_type="class",
                node=node,
                signature=self._signature_until_body(node),
                metadata={"test": name.startswith("Test")},
            )
            self._class_stack.append(name)
            for child in node.children:
                if child.type != "class_body":
                    continue
                for member in child.children:
                    self.visit(member)
            self._class_stack.pop()
            return True
        return False

    def _visit_method_definition(self, node: Node) -> bool:
        name = self._child_name(
            node,
            {"property_identifier", "identifier", "private_property_identifier"},
        )
        if name:
            qualified = ".".join([*self._class_stack, name])
            self._add_symbol(
                name=name,
                symbol_type="method",
                node=node,
                qualified_name=qualified,
                signature=self._signature_until_body(node),
            )
        return False

    def _visit_call_expression(self, node: Node) -> bool:
        function_node = node.child_by_field_name("function") or (
            node.children[0] if node.children else None
        )
        name = self._text(function_node) if function_node else ""
        if name:
            self.calls.append(
                ParsedCall(
                    name=name,
                    line=self._line(node),
                    caller=".".join(self._class_stack) or None,
                )
            )
            if name in {"describe", "it", "test", "expect"}:
                self.exports.append(
                    ParsedExport(
                        name=name,
                        line=self._line(node),
                        export_type="test_block",
                        confidence=0.7,
                    )
                )
        return False

    def _add_symbol(
        self,
        *,
        name: str,
        symbol_type: str,
        node: Node,
        signature: str,
        qualified_name: str | None = None,
        metadata: dict[str, bool] | None = None,
    ) -> None:
        qualified = qualified_name or ".".join([*self._class_stack, name])
        key = (qualified, self._line(node))
        if key in self._seen_symbols:
            return
        self._seen_symbols.add(key)
        self.symbols.append(
            ParsedSymbol(
                qualified_name=qualified,
                simple_name=name,
                symbol_type=symbol_type,
                start_line=self._line(node),
                end_line=node.end_point[0] + 1,
                signature=signature,
                is_test=name in {"describe", "it", "test"} or name.startswith("test"),
                confidence=0.9,
                metadata=metadata or {},
            )
        )

    def _text(self, node: Node | None) -> str:
        if node is None:
            return ""
        return self.source[node.start_byte : node.end_byte]

    def _line(self, node: Node) -> int:
        return node.start_point[0] + 1

    def _first_line(self, text: str) -> str:
        return text.strip().splitlines()[0].strip()

    def _signature_until_body(self, node: Node) -> str:
        text = self._text(node)
        head = text.split("{", 1)[0].strip()
        return re.sub(r"\s+", " ", head)

    def _quoted_module(self, text: str) -> str | None:
        matches = re.findall(r"['\"]([^'\"]+)['\"]", text)
        return matches[-1] if matches else None

    def _default_import_name(self, text: str) -> str | None:
        match = re.match(r"\s*import\s+([\w$]+)\s+from\b", text)
        return match.group(1) if match else None

    def _import_names(self, text: str) -> list[str]:
        named = re.search(r"\{([^}]+)\}", text, re.DOTALL)
        if named:
            return [
                part.strip().split(" as ", 1)[0].strip()
                for part in named.group(1).split(",")
                if part.strip()
            ]
        namespace = re.search(r"import\s+\*\s+as\s+([\w$]+)", text)
        if namespace:
            return [namespace.group(1)]
        default = self._default_import_name(text)
        return [default] if default else []

    def _export_names(self, text: str) -> list[str]:
        patterns: list[Callable[[str], re.Match[str] | None]] = [
            lambda value: re.search(r"export\s+default\s+([\w$]+)", value),
            lambda value: re.search(r"export\s+(?:async\s+)?function\s+([\w$]+)", value),
            lambda value: re.search(r"export\s+class\s+([\w$]+)", value),
            lambda value: re.search(r"export\s+(?:const|let|var)\s+([\w$]+)", value),
        ]
        names = [match.group(1) for pattern in patterns if (match := pattern(text))]
        named = re.search(r"export\s+\{([^}]+)\}", text, re.DOTALL)
        if named:
            names.extend(
                part.strip().split(" as ", 1)[0].strip()
                for part in named.group(1).split(",")
                if part.strip()
            )
        return names or (["default"] if "export default" in text else [])

    def _child_name(self, node: Node, types: set[str]) -> str | None:
        for child in node.children:
            if child.type in types:
                return self._text(child)
        return None
