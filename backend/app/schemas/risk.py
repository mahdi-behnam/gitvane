from pydantic import BaseModel


class RiskBase(BaseModel):
    repository_id: int
