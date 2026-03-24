from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes import chat, email_helper
from app.models.chat import ChatSession, ChatSessionType


class DummyQuery:
    def __init__(self, row):
        self.row = row

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.row


class DummyDB:
    def __init__(self, row):
        self.row = row

    def query(self, model):
        if model is ChatSession:
            return DummyQuery(self.row)
        return DummyQuery(None)


def test_chat_session_endpoint_rejects_email_helper_sessions():
    db = DummyDB(SimpleNamespace(id=42, user_id=7, session_type=ChatSessionType.email_helper))
    current_user = SimpleNamespace(id=7)

    with pytest.raises(HTTPException) as exc:
        chat.get_session(session_id=42, db=db, current_user=current_user)

    assert exc.value.status_code == 403


def test_email_helper_endpoint_rejects_normal_chat_sessions(monkeypatch):
    monkeypatch.setattr(email_helper, 'get_email_helper_enabled', lambda db: True)
    db = DummyDB(SimpleNamespace(id=77, user_id=5, session_type=ChatSessionType.chat))
    current_user = SimpleNamespace(id=5)

    with pytest.raises(HTTPException) as exc:
        email_helper.get_session(session_id=77, db=db, current_user=current_user)

    assert exc.value.status_code == 403
