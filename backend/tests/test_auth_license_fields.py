from types import SimpleNamespace

from fastapi import Response

from app.api.routes import auth
from app.models.user import Role
from app.schemas.auth import LoginRequest


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

    def query(self, _model):
        return DummyQuery(self.row)


def test_login_response_includes_license_fields(monkeypatch):
    user = SimpleNamespace(
        id=7,
        email='admin@example.com',
        role=Role.admin,
        department_id=None,
        password_hash='hash',
        must_change_credentials=True,
    )
    snapshot = SimpleNamespace(
        license_enabled=True,
        license_active=False,
        license_status='inactive',
        grace_until='2026-03-25T00:00:00+00:00',
    )

    monkeypatch.setattr(auth, 'verify_password', lambda _plain, _hash: True)
    monkeypatch.setattr(auth, 'create_access_token', lambda _sub: 'jwt-token')
    monkeypatch.setattr(auth, 'generate_csrf_token', lambda: 'csrf-token')
    monkeypatch.setattr(auth, 'get_email_helper_enabled', lambda _db: True)
    monkeypatch.setattr(auth, 'ensure_runtime_license_snapshot', lambda _db: snapshot)

    response = Response()
    out = auth.login(
        payload=LoginRequest(email='admin@example.com', password='secret'),
        response=response,
        db=DummyDB(user),
    )

    assert out.license_enabled is True
    assert out.license_active is False
    assert out.license_status == 'inactive'
    assert out.license_grace_until == '2026-03-25T00:00:00+00:00'
    assert out.must_change_credentials is True


def test_me_response_includes_license_fields(monkeypatch):
    user = SimpleNamespace(
        id=9,
        email='viewer@example.com',
        role=Role.viewer,
        department_id=2,
        must_change_credentials=False,
    )
    snapshot = SimpleNamespace(
        license_enabled=True,
        license_active=True,
        license_status='grace',
        grace_until='2026-03-26T00:00:00+00:00',
    )

    monkeypatch.setattr(auth, 'get_email_helper_enabled', lambda _db: False)
    monkeypatch.setattr(auth, 'ensure_runtime_license_snapshot', lambda _db: snapshot)

    out = auth.me(current_user=user, db=object())

    assert out.license_enabled is True
    assert out.license_active is True
    assert out.license_status == 'grace'
    assert out.license_grace_until == '2026-03-26T00:00:00+00:00'
    assert out.must_change_credentials is False
