from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ChatMessageSource(Base):
    __tablename__ = 'chat_message_sources'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey('chat_messages.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    source_order: Mapped[int] = mapped_column(Integer, nullable=False)
    document_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    chunk_id: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    csv_row_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    csv_row_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    message = relationship('ChatMessage', back_populates='sources')
