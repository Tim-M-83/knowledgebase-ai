import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FeedbackRating(str, enum.Enum):
    up = 'up'
    down = 'down'


class Feedback(Base):
    __tablename__ = 'feedback'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    message_id: Mapped[int] = mapped_column(ForeignKey('chat_messages.id', ondelete='CASCADE'), nullable=False, index=True)
    rating: Mapped[FeedbackRating] = mapped_column(Enum(FeedbackRating, name='feedback_rating_enum'), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    message = relationship('ChatMessage', back_populates='feedback_items')
