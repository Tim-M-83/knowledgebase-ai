from __future__ import annotations

from types import SimpleNamespace

from app.services import license_manager
from app.services.license_server import LicenseServerError, RemoteActivateResponse, RemoteValidateResponse
from app.services.license_state import LicenseSnapshot


def _snapshot(*, active: bool, status: str) -> LicenseSnapshot:
    return LicenseSnapshot(
        license_enabled=True,
        license_active=active,
        license_status=status,
        workspace_id='workspace-1',
        instance_id_configured=True,
        license_key_configured=True,
        current_period_end='2026-05-01T00:00:00Z' if active else None,
        last_validated_at='2026-03-24T10:00:00Z' if active else None,
        last_checked_at='2026-03-24T10:00:00Z',
        grace_until='2026-03-25T10:00:00Z' if active else None,
        last_error=None,
        license_server_base_url='https://app.automateki.de',
    )


def test_activate_current_installation_stores_and_uses_pasted_license_key(monkeypatch):
    captured: dict[str, str | None] = {}

    monkeypatch.setattr(license_manager.settings, 'license_server_admin_token', '', raising=False)
    monkeypatch.setattr(license_manager, 'ensure_workspace_id', lambda _db: 'workspace-1')
    monkeypatch.setattr(license_manager, 'ensure_machine_fingerprint', lambda _db: 'machine-1')
    monkeypatch.setattr(license_manager, '_company_name', lambda: 'KnowledgeBase AI')
    monkeypatch.setattr(license_manager, '_billing_email', lambda _email=None: 'billing@example.com')
    monkeypatch.setattr(license_manager, '_hostname', lambda: 'host-1')
    monkeypatch.setattr(
        license_manager,
        'store_license_key',
        lambda _db, license_key: captured.__setitem__('stored_key', license_key),
    )
    monkeypatch.setattr(
        license_manager,
        'activate_remote_license',
        lambda **kwargs: captured.update(kwargs)
        or RemoteActivateResponse(
            instance_id='instance-1',
            subscription_status='active',
            subscription_active=True,
            current_period_end='2026-05-01T00:00:00Z',
        ),
    )
    monkeypatch.setattr(
        license_manager,
        'persist_activation',
        lambda _db, **kwargs: _snapshot(active=kwargs['active'], status=kwargs['status']),
    )

    snapshot = license_manager.activate_current_installation(
        db=object(),
        license_key='POLAR-REAL-KEY-001',
        email='admin@example.com',
    )

    assert captured['stored_key'] == 'POLAR-REAL-KEY-001'
    assert captured['license_key'] == 'POLAR-REAL-KEY-001'
    assert snapshot.license_active is True
    assert snapshot.license_status == 'active'


def test_validate_current_license_retries_once_on_activation_not_found(monkeypatch):
    call_order: list[str] = []
    state = {'instance_id': 'instance-old'}

    monkeypatch.setattr(license_manager.settings, 'license_server_admin_token', '', raising=False)
    monkeypatch.setattr(license_manager, 'ensure_workspace_id', lambda _db: 'workspace-1')
    monkeypatch.setattr(license_manager, 'ensure_machine_fingerprint', lambda _db: 'machine-1')
    monkeypatch.setattr(license_manager, 'get_instance_id', lambda _db: state['instance_id'])
    monkeypatch.setattr(license_manager, 'get_stored_license_key', lambda _db: 'POLAR-REAL-KEY-001')

    def fake_validate_remote_license(**kwargs):
        call_order.append(kwargs['instance_id'])
        if kwargs['instance_id'] == 'instance-old':
            return RemoteValidateResponse(allowed=False, status='activation_not_found', current_period_end=None)
        return RemoteValidateResponse(
            allowed=True,
            status='active',
            current_period_end='2026-05-01T00:00:00Z',
        )

    def fake_activate_current_installation(_db, *, license_key=None, email=None):
        state['instance_id'] = 'instance-new'
        call_order.append(f'activate:{license_key}')
        return _snapshot(active=True, status='active')

    monkeypatch.setattr(license_manager, 'validate_remote_license', fake_validate_remote_license)
    monkeypatch.setattr(license_manager, 'activate_current_installation', fake_activate_current_installation)
    monkeypatch.setattr(
        license_manager,
        'persist_validation_result',
        lambda _db, **kwargs: _snapshot(active=kwargs['active'], status=kwargs['status']),
    )

    snapshot = license_manager.validate_current_license(db=object())

    assert call_order == ['instance-old', 'activate:POLAR-REAL-KEY-001', 'instance-new']
    assert snapshot.license_active is True
    assert snapshot.license_status == 'active'


def test_validate_current_license_marks_inactive_after_failed_reactivation(monkeypatch):
    state = {'instance_id': 'instance-old'}
    captured: dict[str, str | bool] = {}

    monkeypatch.setattr(license_manager.settings, 'license_server_admin_token', '', raising=False)
    monkeypatch.setattr(license_manager, 'ensure_workspace_id', lambda _db: 'workspace-1')
    monkeypatch.setattr(license_manager, 'ensure_machine_fingerprint', lambda _db: 'machine-1')
    monkeypatch.setattr(license_manager, 'get_instance_id', lambda _db: state['instance_id'])
    monkeypatch.setattr(license_manager, 'get_stored_license_key', lambda _db: 'POLAR-REAL-KEY-001')
    monkeypatch.setattr(
        license_manager,
        'validate_remote_license',
        lambda **_kwargs: RemoteValidateResponse(
            allowed=False,
            status='activation_not_found',
            current_period_end=None,
        ),
    )

    def fake_activate_current_installation(_db, *, license_key=None, email=None):
        state['instance_id'] = 'instance-recreated'
        return _snapshot(active=True, status='active')

    monkeypatch.setattr(license_manager, 'activate_current_installation', fake_activate_current_installation)
    monkeypatch.setattr(
        license_manager,
        'clear_local_license_state',
        lambda _db, *, status='deactivated', last_error=None, clear_license_key=False: captured.update(
            status=status,
            last_error=last_error or '',
            clear_license_key=clear_license_key,
        )
        or _snapshot(active=False, status=status),
    )

    snapshot = license_manager.validate_current_license(db=object())

    assert snapshot.license_active is False
    assert snapshot.license_status == 'activation_not_found'
    assert captured['clear_license_key'] is False
    assert 'automatic reactivation attempt' in str(captured['last_error'])


def test_validate_license_on_startup_marks_client_errors_inactive_without_grace(monkeypatch):
    monkeypatch.setattr(license_manager, 'get_license_snapshot', lambda _db: _snapshot(active=True, status='active'))
    monkeypatch.setattr(license_manager, 'has_stored_license_key', lambda _db: True)
    monkeypatch.setattr(
        license_manager,
        'validate_current_license',
        lambda _db: (_ for _ in ()).throw(LicenseServerError('License key is invalid.', status_code=403)),
    )
    monkeypatch.setattr(
        license_manager,
        'persist_validation_result',
        lambda _db, **kwargs: _snapshot(active=kwargs['active'], status=kwargs['status']),
    )

    snapshot = license_manager.validate_license_on_startup(db=object())

    assert snapshot.license_active is False
    assert snapshot.license_status == 'license_error'


def test_deactivate_current_license_keeps_stored_license_key(monkeypatch):
    captured: dict[str, str | bool] = {}

    monkeypatch.setattr(license_manager, 'ensure_workspace_id', lambda _db: 'workspace-1')
    monkeypatch.setattr(license_manager, 'get_instance_id', lambda _db: 'instance-1')
    monkeypatch.setattr(license_manager, 'get_stored_license_key', lambda _db: 'POLAR-REAL-KEY-001')
    monkeypatch.setattr(
        license_manager,
        'deactivate_remote_license',
        lambda **kwargs: captured.update(kwargs) or True,
    )
    monkeypatch.setattr(
        license_manager,
        'clear_local_license_state',
        lambda _db, *, status='deactivated', last_error=None, clear_license_key=False: captured.update(
            status=status,
            clear_license_key=clear_license_key,
        )
        or _snapshot(active=False, status=status),
    )

    snapshot = license_manager.deactivate_current_license(db=object())

    assert captured['license_key'] == 'POLAR-REAL-KEY-001'
    assert captured['clear_license_key'] is False
    assert snapshot.license_active is False
    assert snapshot.license_status == 'deactivated'


def test_reset_current_activations_clears_local_instance_and_keeps_key(monkeypatch):
    captured: dict[str, str | bool] = {}

    monkeypatch.setattr(license_manager, 'ensure_workspace_id', lambda _db: 'workspace-1')
    monkeypatch.setattr(
        license_manager,
        'reset_remote_activations',
        lambda **_kwargs: SimpleNamespace(
            current_period_end='2026-05-01T00:00:00Z',
            active_activation_count=0,
            total_activation_count=2,
            activation_limit=3,
        ),
    )
    monkeypatch.setattr(
        license_manager,
        'clear_local_license_state',
        lambda _db, *, status='deactivated', last_error=None, clear_license_key=False: captured.update(
            status=status,
            clear_license_key=clear_license_key,
        )
        or _snapshot(active=False, status=status),
    )

    snapshot = license_manager.reset_current_activations(db=object())

    assert captured['status'] == 'activation_required'
    assert captured['clear_license_key'] is False
    assert snapshot.remote_active_activation_count == 0
    assert snapshot.remote_total_activation_count == 2
    assert snapshot.activation_limit == 3
