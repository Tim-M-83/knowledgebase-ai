from app.api.routes import chat
from app.models.chat import ChatSession


class DummyQuery:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count
        self.model = None
        self.sync_session = None

    def filter(self, *args, **kwargs):
        return self

    def delete(self, synchronize_session=False):
        self.sync_session = synchronize_session
        return self.deleted_count


class DummyDB:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count
        self.query_model = None
        self.committed = False
        self._query = DummyQuery(deleted_count)

    def query(self, model):
        self.query_model = model
        self._query.model = model
        return self._query

    def commit(self):
        self.committed = True


class DummyUser:
    def __init__(self, user_id: int):
        self.id = user_id


def test_clear_sessions_deletes_current_user_sessions(monkeypatch):
    monkeypatch.setattr(chat, 'validate_csrf', lambda request: None)
    db = DummyDB(deleted_count=4)
    result = chat.clear_sessions(request=object(), db=db, current_user=DummyUser(1))

    assert db.query_model is ChatSession
    assert db.committed is True
    assert result == {'deleted_sessions': 4}
