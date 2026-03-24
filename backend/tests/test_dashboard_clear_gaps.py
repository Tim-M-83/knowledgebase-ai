import pytest
from fastapi import HTTPException

from app.api.routes import dashboard
from app.core.rbac import require_roles
from app.models.retrieval_log import RetrievalLog
from app.models.user import Role


class DummyQuery:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count

    def filter(self, *args, **kwargs):
        return self

    def delete(self, synchronize_session=False):
        return self.deleted_count


class DummyDB:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count
        self.query_model = None
        self.committed = False
        self._query = DummyQuery(deleted_count)

    def query(self, model):
        self.query_model = model
        return self._query

    def commit(self):
        self.committed = True


class DummyUser:
    def __init__(self, role: Role):
        self.role = role


def test_clear_gaps_is_admin_only():
    checker = require_roles(Role.admin)
    assert checker(current_user=DummyUser(Role.admin)).role == Role.admin
    with pytest.raises(HTTPException):
        checker(current_user=DummyUser(Role.editor))


def test_clear_gaps_deletes_gap_rows(monkeypatch):
    monkeypatch.setattr(dashboard, 'validate_csrf', lambda request: None)
    db = DummyDB(deleted_count=7)
    result = dashboard.clear_gaps(request=object(), db=db, _=DummyUser(Role.admin))

    assert db.query_model is RetrievalLog
    assert db.committed is True
    assert result == {'deleted_gaps': 7}
