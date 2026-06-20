from pydantic import BaseModel


class ImpactBase(BaseModel):
    repository_id: int
