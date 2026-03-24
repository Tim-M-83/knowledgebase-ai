import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ChatRole(str, enum.Enum):
    user = 'user'
    assistant = 'assistant'
    system = 'system'


class ChatSessionType(str, enum.Enum):
    chat = 'chat'
    email_helper = 'email_helper'


class ChatSession(Base):
    __tablename__ = 'chat_sessions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False, default='New Chat')
    session_type: Mapped[ChatSessionType] = mapped_column(
        Enum(ChatSessionType, name='chat_session_type_enum'),
        nullable=False,
        default=ChatSessionType.chat,
        index=True,
    )
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship('User', back_populates='chat_sessions')
    messages = relationship('ChatMessage', back_populates='session', cascade='all, delete-orphan')
    retrieval_logs = relationship('RetrievalLog', back_populates='session', cascade='all, delete-orphan')


class ChatMessage(Base):
    __tablename__ = 'chat_messages'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    role: Mapped[ChatRole] = mapped_column(Enum(ChatRole, name='chat_role_enum'), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship('ChatSession', back_populates='messages')
    feedback_items = relationship('Feedback', back_populates='message', cascade='all, delete-orphan')
    sources = relationship('ChatMessageSource', back_populates='message', cascade='all, delete-orphan')
