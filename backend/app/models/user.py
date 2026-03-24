import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Role(str, enum.Enum):
    admin = 'admin'
    editor = 'editor'
    viewer = 'viewer'


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, name='role_enum'), nullable=False, default=Role.viewer)
    must_change_credentials: Mapped[bool] = mapped_column(nullable=False, default=False, server_default='false')
    is_bootstrap_admin: Mapped[bool] = mapped_column(nullable=False, default=False, server_default='false')
    department_id: Mapped[int | None] = mapped_column(ForeignKey('departments.id', ondelete='SET NULL'), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    department = relationship('Department', back_populates='users')
    documents = relationship('Document', back_populates='owner')
    summarizer_documents = relationship('SummarizerDocument', back_populates='owner', cascade='all, delete-orphan')
    chat_sessions = relationship('ChatSession', back_populates='user')
    personal_notes = relationship('PersonalNote', back_populates='user', cascade='all, delete-orphan')
