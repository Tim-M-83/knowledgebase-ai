from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes import license
from app.models.user import Role
from app.schemas.license import LicenseActivateIn
from app.services.license_server import LicenseServerError
from app.services.license_state import LicenseSnapshot


def _snapshot(active: bool = False, status: str = 'inactive') -> LicenseSnapshot:
    return LicenseSnapshot(
        license_enabled=True,
        license_active=active,
        license_status=status,
        workspace_id='workspace_1',
        instance_id_configured=active,
        license_key_configured=True,
        current_period_end='2026-12-31' if active else None,
        last_validated_at='2026-03-20T00:00:00+00:00' if active else None,
        last_checked_at='2026-03-20T00:00:00+00:00',
        grace_until='2026-03-25T00:00:00+00:00' if active else None,
        last_error=None,
        license_server_base_url='https://app.automateki.de',
    )


def test_checkout_returns_external_checkout_url(monkeypatch):
    flags = {'csrf': False}

    monkeypatch.setattr(license, 'validate_csrf', lambda _request: flags.__setitem__('csrf', True))
    monkeypatch.setattr(
        license,
        'start_checkout',
        lambda _db, email=None, company_name=None: f'https://app.automateki.de/checkout/{email}',
    )

    out = license.create_checkout(
        request=object(),
        db=object(),
        current_user=SimpleNamespace(id=1, role=Role.admin, email='admin@example.com'),
    )

    assert flags['csrf'] is True
    assert out.url == 'https://app.automateki.de/checkout/admin@example.com'


def test_activate_returns_updated_license_status(monkeypatch):
    monkeypatch.setattr(license, 'validate_csrf', lambda _request: None)
    monkeypatch.setattr(
        license,
        'activate_current_installation',
        lambda _db, license_key=None, email=None: _snapshot(active=True, status='active'),
    )

    out = license.activate(
        payload=LicenseActivateIn(license_key='POLAR-KEY-123'),
        request=object(),
        db=object(),
        current_user=SimpleNamespace(id=1, role=Role.admin, email='admin@automateki.de'),
    )

    assert out.license_active is True
    assert out.license_status == 'active'


def test_validate_translates_license_server_errors(monkeypatch):
    monkeypatch.setattr(license, 'validate_csrf', lambda _request: None)
    monkeypatch.setattr(
        license,
        'validate_current_license',
        lambda _db: (_ for _ in ()).throw(LicenseServerError('server unavailable', status_code=502)),
    )

    with pytest.raises(HTTPException) as exc:
        license.validate(
            request=object(),
            db=object(),
            _=SimpleNamespace(id=1, role=Role.admin),
        )

    assert exc.value.status_code == 502
    assert exc.value.detail == 'server unavailable'


def test_status_returns_remote_activation_usage(monkeypatch):
    monkeypatch.setattr(
        license,
        'get_license_status_view',
        lambda _db: LicenseSnapshot(
            license_enabled=True,
            license_active=False,
            license_status='activation_required',
            workspace_id='workspace_1',
            instance_id_configured=False,
            license_key_configured=True,
            current_period_end=None,
            last_validated_at=None,
            last_checked_at=None,
            grace_until=None,
            last_error=None,
            license_server_base_url='https://app.automateki.de',
            remote_active_activation_count=1,
            remote_total_activation_count=1,
            activation_limit=3,
        ),
    )

    out = license.get_license_status(db=object(), _=SimpleNamespace(id=1))

    assert out.remote_active_activation_count == 1
    assert out.remote_total_activation_count == 1
    assert out.activation_limit == 3


def test_reset_activations_returns_updated_license_status(monkeypatch):
    monkeypatch.setattr(license, 'validate_csrf', lambda _request: None)
    monkeypatch.setattr(
        license,
        'reset_current_activations',
        lambda _db: LicenseSnapshot(
            license_enabled=True,
            license_active=False,
            license_status='activation_required',
            workspace_id='workspace_1',
            instance_id_configured=False,
            license_key_configured=True,
            current_period_end='2026-03-31T00:00:00Z',
            last_validated_at=None,
            last_checked_at='2026-03-24T00:00:00Z',
            grace_until=None,
            last_error=None,
            license_server_base_url='https://app.automateki.de',
            remote_active_activation_count=0,
            remote_total_activation_count=2,
            activation_limit=3,
        ),
    )

    out = license.reset_activations(
        request=object(),
        db=object(),
        _=SimpleNamespace(id=1, role=Role.admin),
    )

    assert out.license_status == 'activation_required'
    assert out.remote_active_activation_count == 0
    assert out.activation_limit == 3
