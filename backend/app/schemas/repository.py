from pydantic import BaseModel


class RepositoryBase(BaseModel):
    name: str
    clone_url: str
