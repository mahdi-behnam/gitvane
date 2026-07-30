from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.impact import ChangedFileInput, TestRecommendationOut


class TestRecommendationRequest(BaseModel):
    repository_id: UUID
    changed_files: list[ChangedFileInput]
    impacted_files: list[str] = Field(default_factory=list)
    top_k: int = Field(10, ge=1, le=100)


class TestRecommendationResponse(BaseModel):
    repository_id: UUID
    changed_files: list[ChangedFileInput]
    recommended_tests: list[TestRecommendationOut]
