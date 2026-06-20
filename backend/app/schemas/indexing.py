from pydantic import BaseModel


class IndexingBase(BaseModel):
    repository_id: int
