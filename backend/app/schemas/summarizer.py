from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

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
    detected_language_code: str | None = None
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


class SummarizerLanguageRequest(BaseModel):
    response_language_mode: Literal['auto', 'document', 'custom'] = 'auto'
    custom_response_language: str | None = None
    browser_language: str | None = None

    @field_validator('custom_response_language')
    @classmethod
    def _strip_custom_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator('browser_language')
    @classmethod
    def _strip_browser_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned[:32] if cleaned else None

    @model_validator(mode='after')
    def _validate_custom_language(self) -> 'SummarizerLanguageRequest':
        if self.response_language_mode == 'custom' and not self.custom_response_language:
            raise ValueError('custom_response_language is required when response_language_mode is custom')
        return self


class SummarizerSummarizeRequest(SummarizerLanguageRequest):
    pass


class SummarizerAskRequest(SummarizerLanguageRequest):
    question: str
