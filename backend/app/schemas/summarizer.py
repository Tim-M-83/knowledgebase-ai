from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.chat import ChatRole
from app.models.summarizer import SummarizerDocumentStatus


class SummarizerDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    original_name: str
    mime_type: str
    size: int
    status: SummarizerDocumentStatus
    error_text: str | None = None
    summary_text: str | None = None
    summary_updated_at: datetime | None = None
    created_at: datetime


class SummarizerDocumentDetail(SummarizerDocumentOut):
    chunk_count: int
    message_count: int


class SummarizerMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    role: ChatRole
    content: str
    created_at: datetime


class SummarizerAskRequest(BaseModel):
    question: str
