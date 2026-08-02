from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class EvaluationBase(BaseModel):
    repository_id: UUID


EvaluationMethod = Literal[
    "dependency_only",
    "semantic_only",
    "cochange_only",
    "hybrid",
]


class EvaluationRunRequest(EvaluationBase):
    name: str = "Historical impact evaluation"
    commit_limit: int = Field(100, ge=1, le=1000)
    methods: list[EvaluationMethod] = Field(
        default_factory=lambda: [
            "dependency_only",
            "semantic_only",
            "cochange_only",
            "hybrid",
        ]
    )
    k_values: list[int] = Field(default_factory=lambda: [5, 10, 20])


class EvaluationRunResponse(BaseModel):
    evaluation_run_id: int
    status: str
    summary: dict[str, Any] = Field(default_factory=dict)


class EvaluationStatusResponse(BaseModel):
    evaluation_run_id: int
    repository_id: UUID
    name: str
    status: str
    methods: list[str]
    commit_limit: int
    summary: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None


class EvaluationReportResponse(BaseModel):
    evaluation_run_id: int
    markdown: str


class EvaluationRunListItem(BaseModel):
    evaluation_run_id: int
    name: str
    status: str
    commit_limit: int
    methods: list[str]
    created_at: str

