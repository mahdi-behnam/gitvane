from pydantic import BaseModel


class GraphBase(BaseModel):
    repository_id: int
