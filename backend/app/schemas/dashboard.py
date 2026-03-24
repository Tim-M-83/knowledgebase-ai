from datetime import datetime
from pydantic import BaseModel


class KpisResponse(BaseModel):
    docs: int
    chunks: int
    users: int
    chats: int
    last_ingestion: datetime | None
    failed_ingestions: int


class TimePoint(BaseModel):
    date: str
    value: int


class LabelValue(BaseModel):
    label: str
    value: int


class ChartsResponse(BaseModel):
    daily_chats: list[TimePoint]
    top_tags: list[LabelValue]
    top_departments: list[LabelValue]
    unanswered_daily: list[TimePoint]


class GapItem(BaseModel):
    id: int
    question: str
    avg_score: float
    had_sources: bool
    created_at: datetime
