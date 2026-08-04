from uuid import UUID

from pydantic import BaseModel, Field


class SearchBase(BaseModel):
    query: str


class SemanticSearchRequest(SearchBase):
    repository_id: UUID
    top_k: int = Field(10, ge=1, le=100)


class SemanticSearchResult(BaseModel):
    path: str
    language: str | None = None
    symbol: str | None = None
    signature: str | None = None
    start_line: int
    end_line: int
    score: float
    snippet: str



class SemanticSearchResponse(BaseModel):
    results: list[SemanticSearchResult]
