from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.chat import ChatRole
from app.models.feedback import FeedbackRating


class ChatSessionCreate(BaseModel):
    title: str | None = 'New Chat'


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    created_at: datetime


class SourceRef(BaseModel):
    id: int
    document_id: int
    original_name: str
    chunk_id: int
    score: float
    page_number: int | None = None
    csv_row_start: int | None = None
    csv_row_end: int | None = None
    snippet: str


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    role: ChatRole
    content: str
    created_at: datetime
    sources: list[SourceRef] = Field(default_factory=list)


class ChatAskFilters(BaseModel):
    department_id: int | None = None
    tag_ids: list[int] | None = None
    visibility: str | None = None


class ChatAskRequest(BaseModel):
    session_id: int | None = None
    question: str
    filters: ChatAskFilters | None = None


class EmailHelperAskRequest(BaseModel):
    session_id: int | None = None
    email_text: str


class FeedbackCreate(BaseModel):
    message_id: int
    rating: FeedbackRating
    comment: str | None = None


class SSEDoneEvent(BaseModel):
    answer: str
    session_id: int
    message_id: int
    low_confidence: bool
    warning: str | None = None
