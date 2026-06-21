from typing import Any

from pydantic import BaseModel, Field


class GraphBase(BaseModel):
    repository_id: int


class GraphNode(BaseModel):
    id: int
    path: str
    language: str
    is_test: bool
    is_generated: bool
    loc: int


class GraphEdge(BaseModel):
    id: int
    source_file_id: int
    target_file_id: int
    source_path: str
    target_path: str
    edge_type: str
    confidence: float
    evidence: dict[str, Any] = Field(default_factory=dict)


class GraphResponse(GraphBase):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
