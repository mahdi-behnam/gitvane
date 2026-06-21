from typing import Any, Literal

from pydantic import BaseModel, Field


class ImpactBase(BaseModel):
    repository_id: int


class ChangedFileInput(BaseModel):
    path: str
    change_type: str = "modified"
    changed_lines: list[tuple[int, int]] = Field(default_factory=list)
    old_path: str | None = None


class ChangedSymbolOut(BaseModel):
    path: str
    qualified_name: str
    symbol_type: str
    start_line: int
    end_line: int


class ImpactReasonOut(BaseModel):
    type: str
    message: str
    confidence: float
    evidence: dict[str, Any] = Field(default_factory=dict)


class TestRecommendationOut(BaseModel):
    path: str
    score: float
    reason: str | None = None
    linked_files: list[str] = Field(default_factory=list)


class ImpactedFileOut(BaseModel):
    rank: int
    path: str
    score: float
    component_scores: dict[str, float]
    reasons: list[ImpactReasonOut]
    recommended_tests: list[TestRecommendationOut] = Field(default_factory=list)


class ImpactAnalyzeRequest(ImpactBase):
    base_ref: str | None = None
    head_ref: str | None = None
    raw_diff: str | None = None
    changed_files: list[ChangedFileInput] | None = None
    top_k: int = Field(20, ge=1, le=100)
    include_explanation: bool = True
    include_changed_files_in_predictions: bool = False
    max_dependency_depth: int = Field(3, ge=1, le=5)


class RiskSummaryOut(BaseModel):
    highest_risk_files: list[dict[str, Any]] = Field(default_factory=list)


class ImpactAnalyzeResponse(BaseModel):
    analysis_run_id: int
    repository_id: int
    base_ref: str | None = None
    head_ref: str | None = None
    changed_files: list[ChangedFileInput]
    changed_symbols: list[ChangedSymbolOut]
    impacted_files: list[ImpactedFileOut]
    recommended_tests: list[TestRecommendationOut]
    risk_summary: RiskSummaryOut
    llm_explanation: str | None = None


class ImpactRunResponse(BaseModel):
    analysis_run_id: int
    repository_id: int
    status: str
    input_mode: Literal["git_diff", "raw_diff", "changed_files"]
    changed_files: list[dict[str, Any]]
    changed_symbols: list[dict[str, Any]]
    predictions: list[ImpactedFileOut]
