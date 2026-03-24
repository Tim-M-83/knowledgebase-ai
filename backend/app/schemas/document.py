from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentStatus, DocumentVisibility


class DocumentCreateMeta(BaseModel):
    title: str | None = None
    tags: list[int] = Field(default_factory=list)
    department_id: int | None = None
    folder_id: int | None = None
    visibility: DocumentVisibility = DocumentVisibility.company


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    filename: str
    original_name: str
    mime_type: str
    size: int
    department_id: int | None = None
    folder_id: int | None = None
    visibility: DocumentVisibility
    status: DocumentStatus
    error_text: str | None = None
    created_at: datetime


class DocumentDetail(DocumentOut):
    chunk_count: int
    tag_ids: list[int]


class DocumentMetadataUpdate(BaseModel):
    department_id: int | None = None
    folder_id: int | None = None
    tag_ids: list[int] | None = None
