from pydantic import BaseModel


class EvaluationBase(BaseModel):
    repository_id: int
