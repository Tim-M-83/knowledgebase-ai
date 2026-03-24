from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str


class Pagination(BaseModel):
    total: int


class Timestamped(BaseModel):
    created_at: datetime
