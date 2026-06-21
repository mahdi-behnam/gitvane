from dataclasses import dataclass, field
from typing import Iterable

import networkx as nx

from app.analysis.import_resolver import ImportResolver
from app.analysis.parser_models import ParsedFile, ParsedImport


@dataclass(frozen=True)
class DependencyEdgeData:
    source_path: str
    target_path: str
    edge_type: str
    confidence: float = 1.0
    evidence: dict[str, object] = field(default_factory=dict)


class DependencyGraph:
    """Build and query file-level dependency graphs."""

    def __init__(self, import_resolver: ImportResolver | None = None) -> None:
        self.import_resolver = import_resolver or ImportResolver()

    def build_edges(
        self,
        parsed_files: Iterable[ParsedFile],
        candidate_paths: set[str] | None = None,
    ) -> list[DependencyEdgeData]:
        parsed_by_path = {parsed.path: parsed for parsed in parsed_files}
        candidates = candidate_paths or set(parsed_by_path)
        edges: list[DependencyEdgeData] = []

        for parsed in parsed_by_path.values():
            for parsed_import in parsed.imports:
                target = self.import_resolver.resolve_import(
                    parsed.path,
                    parsed_import,
                    candidates,
                )
                if target is None or target == parsed.path:
                    continue
                edges.append(
                    DependencyEdgeData(
                        source_path=parsed.path,
                        target_path=target,
                        edge_type=self._edge_type(parsed_import),
                        confidence=parsed_import.confidence,
                        evidence={
                            "module": parsed_import.module,
                            "names": parsed_import.names,
                            "line": parsed_import.line,
                            "import_type": parsed_import.import_type,
                        },
                    )
                )
        return self._deduplicate_edges(edges)

    def build_graph(
        self,
        file_paths: Iterable[str],
        edges: Iterable[DependencyEdgeData],
    ) -> nx.DiGraph:
        graph = nx.DiGraph()
        graph.add_nodes_from(file_paths)
        for edge in edges:
            graph.add_edge(
                edge.source_path,
                edge.target_path,
                edge_type=edge.edge_type,
                confidence=edge.confidence,
                evidence=edge.evidence,
            )
        return graph

    def get_reverse_dependencies(
        self,
        graph: nx.DiGraph,
        file_path: str,
        max_depth: int = 1,
    ) -> dict[str, int]:
        """Return files that depend on file_path, mapped to graph distance."""
        if file_path not in graph:
            return {}
        reverse_graph = graph.reverse(copy=False)
        distances = nx.single_source_shortest_path_length(
            reverse_graph, file_path, cutoff=max_depth
        )
        return {
            path: distance
            for path, distance in distances.items()
            if path != file_path and distance > 0
        }

    def _edge_type(self, parsed_import: ParsedImport) -> str:
        return "test_import" if parsed_import.import_type == "test_import" else "import"

    def _deduplicate_edges(
        self, edges: Iterable[DependencyEdgeData]
    ) -> list[DependencyEdgeData]:
        seen: set[tuple[str, str, str]] = set()
        deduped: list[DependencyEdgeData] = []
        for edge in edges:
            key = (edge.source_path, edge.target_path, edge.edge_type)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(edge)
        return deduped
