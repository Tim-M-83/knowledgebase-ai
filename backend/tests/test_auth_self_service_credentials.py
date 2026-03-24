from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response

from app.api.routes import auth
from app.schemas.auth import CredentialUpdateRequest


class DummyQuery:
    def __init__(self, row=None):
        self.row = row

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.row


class DummyDB:
    def __init__(self, duplicate_email_row=None):
        self.duplicate_email_row = duplicate_email_row
        self.committed = False

    def query(self, _model):
        return DummyQuery(row=self.duplicate_email_row)

    def commit(self):
        self.committed = True


def _allow_csrf(monkeypatch):
    monkeypatch.setattr(auth, 'validate_csrf', lambda _request: None)


def test_update_credentials_email_only_updates_user_and_clears_cookies(monkeypatch):
    _allow_csrf(monkeypatch)
    monkeypatch.setattr(auth, 'verify_password', lambda plain, hashed: plain == 'correct' and hashed == 'old-hash')

    user = SimpleNamespace(
        id=1,
        email='old@example.com',
        password_hash='old-hash',
        must_change_credentials=False,
        is_bootstrap_admin=False,
    )
    db = DummyDB(duplicate_email_row=None)
    response = Response()

    out = auth.update_my_credentials(
        payload=CredentialUpdateRequest(
            current_password='correct',
            new_email='new@example.com',
        ),
        request=object(),
        response=response,
        db=db,
        current_user=user,
    )

    cookies = response.headers.getlist('set-cookie')
    assert out.message == 'Credentials updated. Please sign in again.'
    assert user.email == 'new@example.com'
    assert user.password_hash == 'old-hash'
    assert user.must_change_credentials is False
    assert user.is_bootstrap_admin is False
    assert db.committed is True
    assert any(auth.settings.jwt_cookie_name in item for item in cookies)
    assert any(auth.settings.csrf_cookie_name in item for item in cookies)


def test_update_credentials_password_only_updates_hash(monkeypatch):
    _allow_csrf(monkeypatch)
    monkeypatch.setattr(auth, 'verify_password', lambda _plain, _hashed: True)
    monkeypatch.setattr(auth, 'get_password_hash', lambda value: f'hash:{value}')

    user = SimpleNamespace(
        id=1,
        email='old@example.com',
        password_hash='old-hash',
        must_change_credentials=False,
        is_bootstrap_admin=False,
    )
    db = DummyDB()

    auth.update_my_credentials(
        payload=CredentialUpdateRequest(
            current_password='correct',
            new_password='new-password-123',
        ),
        request=object(),
        response=Response(),
        db=db,
        current_user=user,
    )

    assert user.email == 'old@example.com'
    assert user.password_hash == 'hash:new-password-123'
    assert user.must_change_credentials is False
    assert db.committed is True


def test_update_credentials_email_and_password_updates_both(monkeypatch):
    _allow_csrf(monkeypatch)
    monkeypatch.setattr(auth, 'verify_password', lambda _plain, _hashed: True)
    monkeypatch.setattr(auth, 'get_password_hash', lambda value: f'hash:{value}')

    user = SimpleNamespace(
        id=7,
        email='old@example.com',
        password_hash='old-hash',
        must_change_credentials=False,
        is_bootstrap_admin=False,
    )
    db = DummyDB(duplicate_email_row=None)

    auth.update_my_credentials(
        payload=CredentialUpdateRequest(
            current_password='correct',
            new_email='updated@example.com',
            new_password='new-password-123',
        ),
        request=object(),
        response=Response(),
        db=db,
        current_user=user,
    )

    assert user.email == 'updated@example.com'
    assert user.password_hash == 'hash:new-password-123'
    assert user.must_change_credentials is False
    assert user.is_bootstrap_admin is False
    assert db.committed is True


def test_update_credentials_rejects_wrong_current_password(monkeypatch):
    _allow_csrf(monkeypatch)
    monkeypatch.setattr(auth, 'verify_password', lambda _plain, _hashed: False)

    user = SimpleNamespace(
        id=1,
        email='old@example.com',
        password_hash='old-hash',
        must_change_credentials=False,
        is_bootstrap_admin=False,
    )
    db = DummyDB()

    with pytest.raises(HTTPException) as exc:
        auth.update_my_credentials(
            payload=CredentialUpdateRequest(current_password='wrong', new_password='new-password'),
            request=object(),
            response=Response(),
            db=db,
            current_user=user,
        )

    assert exc.value.status_code == 401
    assert 'incorrect' in str(exc.value.detail)
    assert db.committed is False


def test_update_credentials_requires_current_password_for_normal_users(monkeypatch):
    _allow_csrf(monkeypatch)

    user = SimpleNamespace(
        id=1,
        email='old@example.com',
        password_hash='old-hash',
        must_change_credentials=False,
        is_bootstrap_admin=False,
    )
    db = DummyDB()

    with pytest.raises(HTTPException) as exc:
        auth.update_my_credentials(
            payload=CredentialUpdateRequest(new_password='new-password'),
            request=object(),
            response=Response(),
            db=db,
            current_user=user,
        )

    assert exc.value.status_code == 400
    assert 'current_password is required' in str(exc.value.detail)
    assert db.committed is False


def test_update_credentials_rejects_when_no_new_values_given(monkeypatch):
    _allow_csrf(monkeypatch)
    monkeypatch.setattr(auth, 'verify_password', lambda _plain, _hashed: True)

    user = SimpleNamespace(
        id=1,
        email='old@example.com',
        password_hash='old-hash',
        must_change_credentials=False,
        is_bootstrap_admin=False,
    )
    db = DummyDB()

    with pytest.raises(HTTPException) as exc:
        auth.update_my_credentials(
            payload=CredentialUpdateRequest(current_password='correct'),
            request=object(),
            response=Response(),
            db=db,
            current_user=user,
        )

    assert exc.value.status_code == 400
    assert 'At least one of new_email or new_password' in str(exc.value.detail)


def test_update_credentials_rejects_duplicate_target_email(monkeypatch):
    _allow_csrf(monkeypatch)
    monkeypatch.setattr(auth, 'verify_password', lambda _plain, _hashed: True)

    user = SimpleNamespace(
        id=1,
        email='old@example.com',
        password_hash='old-hash',
        must_change_credentials=False,
        is_bootstrap_admin=False,
    )
    db = DummyDB(duplicate_email_row=SimpleNamespace(id=99))

    with pytest.raises(HTTPException) as exc:
        auth.update_my_credentials(
            payload=CredentialUpdateRequest(current_password='correct', new_email='existing@example.com'),
            request=object(),
            response=Response(),
            db=db,
            current_user=user,
        )

    assert exc.value.status_code == 400
    assert 'Email already exists' in str(exc.value.detail)


def test_bootstrap_admin_must_change_both_email_and_password(monkeypatch):
    _allow_csrf(monkeypatch)

    user = SimpleNamespace(
        id=11,
        email='admin@local',
        password_hash='old-hash',
        must_change_credentials=True,
        is_bootstrap_admin=True,
    )
    db = DummyDB()

    with pytest.raises(HTTPException) as exc:
        auth.update_my_credentials(
            payload=CredentialUpdateRequest(new_email='owner@example.com'),
            request=object(),
            response=Response(),
            db=db,
            current_user=user,
        )

    assert exc.value.status_code == 400
    assert 'Bootstrap admin must update both email and password' in str(exc.value.detail)


def test_bootstrap_admin_update_clears_bootstrap_flags(monkeypatch):
    _allow_csrf(monkeypatch)
    monkeypatch.setattr(auth, 'get_password_hash', lambda value: f'hash:{value}')

    user = SimpleNamespace(
        id=11,
        email='admin@local',
        password_hash='old-hash',
        must_change_credentials=True,
        is_bootstrap_admin=True,
    )
    db = DummyDB()

    auth.update_my_credentials(
        payload=CredentialUpdateRequest(
            new_email='owner@example.com',
            new_password='new-password-123',
        ),
        request=object(),
        response=Response(),
        db=db,
        current_user=user,
    )

    assert user.email == 'owner@example.com'
    assert user.password_hash == 'hash:new-password-123'
    assert user.must_change_credentials is False
    assert user.is_bootstrap_admin is False
