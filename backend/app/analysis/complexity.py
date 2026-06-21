import ast
import re

from app.analysis.languages import Language


class ComplexityCalculator:
    """Estimate code complexity from source text without executing it."""

    JS_BRANCH_PATTERN = re.compile(
        r"\b(if|for|while|switch|catch)\b|\?|&&|\|\|",
        re.MULTILINE,
    )

    def score(self, content: str, language: Language | str) -> float:
        branch_count = self.branch_count(content, language)
        nesting = self.max_nesting_depth(content, language)
        function_count = self.function_count(content, language)
        raw = branch_count * 0.08 + nesting * 0.12 + function_count * 0.03
        return round(max(0.0, min(raw, 1.0)), 4)

    def branch_count(self, content: str, language: Language | str) -> int:
        if str(language) in {Language.PYTHON.value, "Language.PYTHON"}:
            return self._python_branch_count(content)
        if str(language) in {
            Language.JAVASCRIPT.value,
            Language.TYPESCRIPT.value,
            "Language.JAVASCRIPT",
            "Language.TYPESCRIPT",
        }:
            return len(self.JS_BRANCH_PATTERN.findall(content))
        return 0

    def function_count(self, content: str, language: Language | str) -> int:
        if str(language) in {Language.PYTHON.value, "Language.PYTHON"}:
            try:
                tree = ast.parse(content)
            except SyntaxError:
                return 0
            return sum(
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                for node in ast.walk(tree)
            )
        return len(re.findall(r"\bfunction\b|=>", content))

    def max_nesting_depth(self, content: str, language: Language | str) -> int:
        if str(language) in {Language.PYTHON.value, "Language.PYTHON"}:
            try:
                return _PythonNestingVisitor.from_source(content).max_depth
            except SyntaxError:
                return 0
        max_depth = depth = 0
        for char in content:
            if char == "{":
                depth += 1
                max_depth = max(max_depth, depth)
            elif char == "}":
                depth = max(depth - 1, 0)
        return max_depth

    def _python_branch_count(self, content: str) -> int:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return 0
        branch_nodes = (
            ast.If,
            ast.For,
            ast.AsyncFor,
            ast.While,
            ast.Try,
            ast.ExceptHandler,
            ast.IfExp,
            ast.BoolOp,
            ast.Match,
        )
        return sum(isinstance(node, branch_nodes) for node in ast.walk(tree))


class _PythonNestingVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.depth = 0
        self.max_depth = 0

    @classmethod
    def from_source(cls, source: str) -> "_PythonNestingVisitor":
        visitor = cls()
        visitor.visit(ast.parse(source))
        return visitor

    def generic_visit(self, node: ast.AST) -> None:
        branch_nodes = (
            ast.If,
            ast.For,
            ast.AsyncFor,
            ast.While,
            ast.Try,
            ast.ExceptHandler,
            ast.With,
            ast.AsyncWith,
            ast.Match,
        )
        if isinstance(node, branch_nodes):
            self.depth += 1
            self.max_depth = max(self.max_depth, self.depth)
            super().generic_visit(node)
            self.depth -= 1
        else:
            super().generic_visit(node)
