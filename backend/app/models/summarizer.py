import enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.db.base import Base
from app.models.chat import ChatRole


settings = get_settings()


class SummarizerDocumentStatus(str, enum.Enum):
    uploaded = 'uploaded'
    processing = 'processing'
    ready = 'ready'
    failed = 'failed'


class SummarizerDocument(Base):
    __tablename__ = 'summarizer_documents'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[SummarizerDocumentStatus] = mapped_column(
        Enum(SummarizerDocumentStatus, name='summarizer_document_status_enum'),
        nullable=False,
        default=SummarizerDocumentStatus.uploaded,
        index=True,
    )
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_updated_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship('User', back_populates='summarizer_documents')
    chunks = relationship('SummarizerChunk', back_populates='document', cascade='all, delete-orphan')
    messages = relationship('SummarizerMessage', back_populates='document', cascade='all, delete-orphan')


class SummarizerChunk(Base):
    __tablename__ = 'summarizer_chunks'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey('summarizer_documents.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dimension), nullable=False)
    meta: Mapped[dict] = mapped_column('metadata', JSONB, nullable=False, default=dict)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document = relationship('SummarizerDocument', back_populates='chunks')


class SummarizerMessage(Base):
    __tablename__ = 'summarizer_messages'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey('summarizer_documents.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    role: Mapped[ChatRole] = mapped_column(Enum(ChatRole, name='chat_role_enum'), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document = relationship('SummarizerDocument', back_populates='messages')
