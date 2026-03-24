import enum

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentVisibility(str, enum.Enum):
    company = 'company'
    department = 'department'
    private = 'private'


class DocumentStatus(str, enum.Enum):
    uploaded = 'uploaded'
    processing = 'processing'
    ready = 'ready'
    failed = 'failed'


class Document(Base):
    __tablename__ = 'documents'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    department_id: Mapped[int | None] = mapped_column(ForeignKey('departments.id', ondelete='SET NULL'), nullable=True)
    folder_id: Mapped[int | None] = mapped_column(ForeignKey('folders.id', ondelete='SET NULL'), nullable=True, index=True)
    visibility: Mapped[DocumentVisibility] = mapped_column(
        Enum(DocumentVisibility, name='document_visibility_enum'),
        nullable=False,
        default=DocumentVisibility.company,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name='document_status_enum'),
        nullable=False,
        default=DocumentStatus.uploaded,
    )
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship('User', back_populates='documents')
    department = relationship('Department', back_populates='documents')
    folder = relationship('Folder', back_populates='documents')
    chunks = relationship('Chunk', back_populates='document', cascade='all, delete-orphan')
    document_tags = relationship('DocumentTag', back_populates='document', cascade='all, delete-orphan')


class DocumentTag(Base):
    __tablename__ = 'document_tags'
    __table_args__ = (
        UniqueConstraint('document_id', 'tag_id', name='uq_document_tag'),
        Index('ix_document_tags_tag_id', 'tag_id'),
    )

    document_id: Mapped[int] = mapped_column(ForeignKey('documents.id', ondelete='CASCADE'), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)

    document = relationship('Document', back_populates='document_tags')
    tag = relationship('Tag', back_populates='documents')
