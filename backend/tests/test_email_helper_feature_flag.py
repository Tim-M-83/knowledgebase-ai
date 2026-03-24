import pytest
from fastapi import HTTPException

from app.api.routes import email_helper
from app.services.feature_flags import get_email_helper_enabled


class DummySetting:
    def __init__(self, value: str):
        self.value = value


class DummyQuery:
    def __init__(self, item):
        self.item = item

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.item


class DummyDB:
    def __init__(self, item):
        self.item = item

    def query(self, model):
        return DummyQuery(self.item)


def test_get_email_helper_enabled_defaults_true_without_db():
    assert get_email_helper_enabled(None) is True


def test_get_email_helper_enabled_reads_false_value_from_settings():
    db = DummyDB(DummySetting('false'))
    assert get_email_helper_enabled(db) is False


def test_get_email_helper_enabled_falls_back_on_invalid_value():
    db = DummyDB(DummySetting('not-a-bool'))
    assert get_email_helper_enabled(db) is True


def test_email_helper_rejects_requests_when_disabled(monkeypatch):
    monkeypatch.setattr(email_helper, 'get_email_helper_enabled', lambda db: False)

    with pytest.raises(HTTPException) as exc:
        email_helper.list_sessions(db=object(), current_user=object())

    assert exc.value.status_code == 403
    assert 'disabled' in str(exc.value.detail).lower()
