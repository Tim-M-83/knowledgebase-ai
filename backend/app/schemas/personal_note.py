from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

PersonalNotePriority = Literal['none', 'low', 'medium', 'high']


class PersonalNoteCreate(BaseModel):
    title: str
    content: str
    priority: str = 'none'


class PersonalNoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    priority: str | None = None


class PersonalNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    content: str
    priority: PersonalNotePriority
    created_at: datetime
    updated_at: datetime
