from app.analysis.dependency_graph import DependencyGraph
from app.analysis.languages import Language
from app.analysis.parser_models import ParsedFile, ParsedImport


def test_resolves_python_import_edges() -> None:
    graph_builder = DependencyGraph()
    parsed_files = [
        ParsedFile(
            path="src/api/routes.py",
            language=Language.PYTHON,
            imports=[ParsedImport(module="src.auth.token", line=1)],
        ),
        ParsedFile(path="src/auth/token.py", language=Language.PYTHON),
    ]

    edges = graph_builder.build_edges(parsed_files)

    assert len(edges) == 1
    assert edges[0].source_path == "src/api/routes.py"
    assert edges[0].target_path == "src/auth/token.py"
    assert edges[0].evidence["module"] == "src.auth.token"


def test_resolves_relative_python_import_edges() -> None:
    graph_builder = DependencyGraph()
    parsed_files = [
        ParsedFile(
            path="pkg/api/routes.py",
            language=Language.PYTHON,
            imports=[ParsedImport(module="auth.token", level=2, line=2)],
        ),
        ParsedFile(path="pkg/auth/token.py", language=Language.PYTHON),
    ]

    edges = graph_builder.build_edges(parsed_files)

    assert edges[0].target_path == "pkg/auth/token.py"


def test_resolves_python_from_import_module_names() -> None:
    graph_builder = DependencyGraph()
    parsed_files = [
        ParsedFile(
            path="src/api/routes.py",
            language=Language.PYTHON,
            imports=[ParsedImport(module="src.auth", names=["token"], line=1)],
        ),
        ParsedFile(path="src/auth/token.py", language=Language.PYTHON),
    ]

    edges = graph_builder.build_edges(parsed_files)

    assert edges[0].target_path == "src/auth/token.py"


def test_resolves_js_ts_relative_import_edges() -> None:
    graph_builder = DependencyGraph()
    parsed_files = [
        ParsedFile(
            path="src/api/routes.ts",
            language=Language.TYPESCRIPT,
            imports=[ParsedImport(module="../auth/token", line=1)],
        ),
        ParsedFile(path="src/auth/token.ts", language=Language.TYPESCRIPT),
    ]

    edges = graph_builder.build_edges(parsed_files)

    assert edges[0].target_path == "src/auth/token.ts"


def test_get_reverse_dependencies_returns_distances() -> None:
    graph_builder = DependencyGraph()
    edges = graph_builder.build_edges(
        [
            ParsedFile(
                path="src/api/routes.py",
                language=Language.PYTHON,
                imports=[ParsedImport(module="src.auth.token")],
            ),
            ParsedFile(
                path="src/ui/view.py",
                language=Language.PYTHON,
                imports=[ParsedImport(module="src.api.routes")],
            ),
            ParsedFile(path="src/auth/token.py", language=Language.PYTHON),
        ]
    )
    graph = graph_builder.build_graph(
        {"src/api/routes.py", "src/ui/view.py", "src/auth/token.py"},
        edges,
    )

    distances = graph_builder.get_reverse_dependencies(
        graph, "src/auth/token.py", max_depth=2
    )

    assert distances == {"src/api/routes.py": 1, "src/ui/view.py": 2}
