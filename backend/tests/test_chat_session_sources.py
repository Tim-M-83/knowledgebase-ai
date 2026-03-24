from datetime import UTC, datetime
from types import SimpleNamespace

from app.api.routes import chat
from app.models.chat import ChatRole, ChatSession, ChatSessionType
from app.models.chat_message_source import ChatMessageSource


class DummyQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class DummyDB:
    def __init__(self, session_row, message_rows, source_rows):
        self.session_row = session_row
        self.message_rows = message_rows
        self.source_rows = source_rows

    def query(self, model):
        if model is ChatSession:
            return DummyQuery([self.session_row] if self.session_row else [])
        if model is chat.ChatMessage:
            return DummyQuery(self.message_rows)
        if model is ChatMessageSource:
            return DummyQuery(self.source_rows)
        raise AssertionError(f'Unexpected model {model}')


def test_get_session_returns_sources_for_assistant_messages():
    session = SimpleNamespace(id=11, user_id=5, session_type=ChatSessionType.chat)
    messages = [
        SimpleNamespace(
            id=101,
            session_id=11,
            role=ChatRole.user,
            content='Question',
            created_at=datetime.now(UTC),
        ),
        SimpleNamespace(
            id=102,
            session_id=11,
            role=ChatRole.assistant,
            content='Answer [1]',
            created_at=datetime.now(UTC),
        ),
    ]
    source_rows = [
        SimpleNamespace(
            id=1,
            message_id=102,
            source_order=1,
            document_id=7,
            original_name='doc.txt',
            chunk_id=22,
            score=0.9,
            page_number=None,
            csv_row_start=None,
            csv_row_end=None,
            snippet='relevant snippet',
        )
    ]

    db = DummyDB(session_row=session, message_rows=messages, source_rows=source_rows)
    current_user = SimpleNamespace(id=5)
    out = chat.get_session(session_id=11, db=db, current_user=current_user)

    assistant = next(item for item in out if item.role == ChatRole.assistant)
    assert len(assistant.sources) == 1
    assert assistant.sources[0].document_id == 7
