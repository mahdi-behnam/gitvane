from typing import Any

from pydantic import BaseModel, Field


class RiskBase(BaseModel):
    repository_id: int


class RiskFileOut(BaseModel):
    path: str
    risk_score: float
    components: dict[str, float] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)


class RepositoryRiskResponse(RiskBase):
    files: list[RiskFileOut]
    metadata: dict[str, Any] = Field(default_factory=dict)
