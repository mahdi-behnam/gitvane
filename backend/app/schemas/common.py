from pydantic import BaseModel


class StatusMessage(BaseModel):
    status: str
    message: str
