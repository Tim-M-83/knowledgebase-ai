from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import main
from app.models.user import Role


class DummyQuery:
    def __init__(self, row):
        self.row = row

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.row


class DummyDB:
    def __init__(self, role: Role, must_change_credentials: bool = False):
        self.row = SimpleNamespace(
            id=1,
            email='admin@local',
            role=role,
            department_id=None,
            must_change_credentials=must_change_credentials,
        )

    def query(self, _model):
        return DummyQuery(self.row)

    def close(self):
        return None


def test_license_guard_blocks_protected_routes_when_license_inactive(monkeypatch):
    monkeypatch.setattr(main.settings, 'license_enforcement_enabled', True, raising=False)
    monkeypatch.setattr(main, 'ensure_bootstrap_admin', lambda _db: None)
    monkeypatch.setattr(main, 'decode_access_token', lambda _token: {'sub': '1'})
    monkeypatch.setattr(main, 'has_runtime_license_access', lambda _db: False)
    monkeypatch.setattr(main, 'SessionLocal', lambda: DummyDB(Role.viewer))

    client = TestClient(main.app)
    response = client.get('/documents', cookies={main.settings.jwt_cookie_name: 'token'})

    assert response.status_code == 403
    assert 'License inactive' in response.text


def test_bootstrap_guard_blocks_protected_routes_until_credentials_changed(monkeypatch):
    monkeypatch.setattr(main.settings, 'license_enforcement_enabled', False, raising=False)
    monkeypatch.setattr(main, 'ensure_bootstrap_admin', lambda _db: None)
    monkeypatch.setattr(main, 'decode_access_token', lambda _token: {'sub': '1'})
    monkeypatch.setattr(main, 'SessionLocal', lambda: DummyDB(Role.admin, must_change_credentials=True))

    client = TestClient(main.app)
    response = client.get('/documents', cookies={main.settings.jwt_cookie_name: 'token'})

    assert response.status_code == 403
    assert 'Initial security setup required' in response.text


def test_bootstrap_guard_allows_auth_me_while_credentials_must_change(monkeypatch):
    monkeypatch.setattr(main.settings, 'license_enforcement_enabled', False, raising=False)
    monkeypatch.setattr(main, 'ensure_bootstrap_admin', lambda _db: None)
    monkeypatch.setattr(main, 'decode_access_token', lambda _token: {'sub': '1'})
    monkeypatch.setattr(main, 'SessionLocal', lambda: DummyDB(Role.admin, must_change_credentials=True))
    monkeypatch.setattr(main.auth, 'get_email_helper_enabled', lambda _db: True)
    monkeypatch.setattr(
        main.auth,
        'ensure_runtime_license_snapshot',
        lambda _db: SimpleNamespace(
            license_enabled=False,
            license_active=True,
            license_status='active',
            grace_until=None,
        ),
    )
    main.app.dependency_overrides[main.auth.get_current_user] = lambda: DummyDB(
        Role.admin,
        must_change_credentials=True,
    ).row

    client = TestClient(main.app)
    try:
        response = client.get('/auth/me', cookies={main.settings.jwt_cookie_name: 'token'})
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200


def test_license_guard_allows_auth_me_credentials_while_license_inactive(monkeypatch):
    monkeypatch.setattr(main.settings, 'license_enforcement_enabled', True, raising=False)
    monkeypatch.setattr(main, 'ensure_bootstrap_admin', lambda _db: None)
    monkeypatch.setattr(main, 'decode_access_token', lambda _token: {'sub': '1'})
    monkeypatch.setattr(main, 'has_runtime_license_access', lambda _db: False)
    monkeypatch.setattr(main, 'SessionLocal', lambda: DummyDB(Role.admin, must_change_credentials=True))
    main.app.dependency_overrides[main.auth.get_current_user] = lambda: DummyDB(
        Role.admin,
        must_change_credentials=True,
    ).row

    def fake_db():
        yield DummyDB(Role.admin, must_change_credentials=True)

    main.app.dependency_overrides[main.auth.get_db] = fake_db
    monkeypatch.setattr(main.auth, 'validate_csrf', lambda _request: None)

    client = TestClient(main.app)
    try:
        response = client.put(
            '/auth/me/credentials',
            json={'new_email': 'owner@example.com', 'new_password': 'new-password-123'},
            cookies={main.settings.jwt_cookie_name: 'token'},
        )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code != 403
    assert 'License inactive' not in response.text


def test_license_guard_still_blocks_dashboard_while_license_inactive(monkeypatch):
    monkeypatch.setattr(main.settings, 'license_enforcement_enabled', True, raising=False)
    monkeypatch.setattr(main, 'ensure_bootstrap_admin', lambda _db: None)
    monkeypatch.setattr(main, 'decode_access_token', lambda _token: {'sub': '1'})
    monkeypatch.setattr(main, 'has_runtime_license_access', lambda _db: False)
    monkeypatch.setattr(main, 'SessionLocal', lambda: DummyDB(Role.admin, must_change_credentials=False))

    client = TestClient(main.app)
    response = client.get('/dashboard', cookies={main.settings.jwt_cookie_name: 'token'})

    assert response.status_code == 403
    assert 'License inactive' in response.text
