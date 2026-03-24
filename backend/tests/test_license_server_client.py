import pytest

from app.services import license_server


class _Response:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ''):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    @property
    def is_error(self) -> bool:
        return self.status_code >= 400

    def json(self):
        if self._payload is None:
            raise ValueError('no json payload')
        return self._payload


class _Client:
    def __init__(self, response: _Response):
        self.response = response

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def request(self, method: str, path: str, json: dict | None = None):
        return self.response


def test_admin_request_401_points_to_license_server_admin_token(monkeypatch):
    monkeypatch.setattr(license_server, '_base_url', lambda: 'https://app.automateki.de')
    monkeypatch.setattr(license_server, '_admin_headers', lambda: {'Authorization': 'Bearer invalid'})
    monkeypatch.setattr(
        license_server.httpx,
        'Client',
        lambda **kwargs: _Client(_Response(401, payload={'detail': 'Invalid bearer token.'})),
    )

    with pytest.raises(license_server.LicenseServerError) as exc:
        license_server.sync_remote_customer(workspace_id='workspace-1')

    assert exc.value.status_code == 401
    assert str(exc.value) == 'License server admin authentication failed. Update LICENSE_SERVER_ADMIN_TOKEN.'


def test_public_license_request_preserves_public_error_detail(monkeypatch):
    monkeypatch.setattr(license_server, '_base_url', lambda: 'https://app.automateki.de')
    monkeypatch.setattr(license_server, '_json_headers', lambda: {'Accept': 'application/json'})
    monkeypatch.setattr(
        license_server.httpx,
        'Client',
        lambda **kwargs: _Client(_Response(403, payload={'detail': 'License key is invalid.'})),
    )

    with pytest.raises(license_server.LicenseServerError) as exc:
        license_server.activate_remote_license(
            workspace_id='workspace-1',
            company_name='KnowledgeBase AI',
            email='billing@example.com',
            license_key='POLAR-KEY',
            machine_fingerprint='machine-1',
            hostname='host-1',
        )

    assert exc.value.status_code == 403
    assert str(exc.value) == 'License key is invalid.'


def test_fetch_remote_status_includes_activation_usage(monkeypatch):
    monkeypatch.setattr(license_server, '_base_url', lambda: 'https://app.automateki.de')
    monkeypatch.setattr(license_server, '_json_headers', lambda: {'Accept': 'application/json'})
    monkeypatch.setattr(
        license_server.httpx,
        'Client',
        lambda **kwargs: _Client(
            _Response(
                200,
                payload={
                    'workspace_id': 'workspace-1',
                    'subscription_status': 'trialing',
                    'subscription_active': True,
                    'current_period_end': '2026-03-31T00:00:00Z',
                    'active_activation_count': 1,
                    'total_activation_count': 2,
                    'activation_limit': 3,
                },
            )
        ),
    )

    status = license_server.fetch_remote_status(workspace_id='workspace-1')

    assert status.subscription_status == 'trialing'
    assert status.active_activation_count == 1
    assert status.total_activation_count == 2
    assert status.activation_limit == 3


def test_reset_remote_activations_returns_updated_counts(monkeypatch):
    monkeypatch.setattr(license_server, '_base_url', lambda: 'https://app.automateki.de')
    monkeypatch.setattr(license_server, '_admin_headers', lambda: {'Authorization': 'Bearer valid'})
    monkeypatch.setattr(
        license_server.httpx,
        'Client',
        lambda **kwargs: _Client(
            _Response(
                200,
                payload={
                    'workspace_id': 'workspace-1',
                    'deactivated_count': 2,
                    'active_activation_count': 0,
                    'total_activation_count': 2,
                    'activation_limit': 3,
                    'subscription_status': 'trialing',
                    'subscription_active': True,
                },
            )
        ),
    )

    result = license_server.reset_remote_activations(workspace_id='workspace-1')

    assert result.workspace_id == 'workspace-1'
    assert result.deactivated_count == 2
    assert result.active_activation_count == 0
    assert result.activation_limit == 3
