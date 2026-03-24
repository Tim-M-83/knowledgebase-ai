from datetime import datetime, timedelta, timezone

from app.services import license_state
from app.services.license_state import LicenseSnapshot


def test_get_license_snapshot_marks_missing_license_as_not_configured(monkeypatch):
    monkeypatch.setattr(license_state, 'ensure_workspace_id', lambda _db: 'workspace_1')
    monkeypatch.setattr(license_state, 'get_instance_id', lambda _db: None)
    monkeypatch.setattr(license_state, '_get_setting_value', lambda _db, _key: None)
    monkeypatch.setattr(license_state.settings, 'license_enforcement_enabled', True, raising=False)

    snapshot = license_state.get_license_snapshot(db=object())

    assert snapshot.license_status == 'activation_required'
    assert snapshot.license_active is False
    assert snapshot.license_key_configured is False


def test_get_license_snapshot_uses_grace_window_for_access(monkeypatch):
    future_grace = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    values = {
        license_state.KEY_LICENSE_STATUS: 'grace',
        license_state.KEY_LICENSE_ACTIVE: 'false',
        license_state.KEY_LICENSE_GRACE_UNTIL: future_grace,
    }

    monkeypatch.setattr(license_state, 'ensure_workspace_id', lambda _db: 'workspace_1')
    monkeypatch.setattr(license_state, 'get_instance_id', lambda _db: 'instance_1')
    monkeypatch.setattr(license_state, '_get_setting_value', lambda _db, key: values.get(key))

    snapshot = license_state.get_license_snapshot(db=object())

    assert snapshot.license_status == 'grace'
    assert snapshot.license_active is True


def test_should_revalidate_after_interval(monkeypatch):
    monkeypatch.setattr(license_state.settings, 'license_validate_interval_hours', 6, raising=False)
    stale_timestamp = (datetime.now(timezone.utc) - timedelta(hours=7)).isoformat()
    snapshot = LicenseSnapshot(
        license_enabled=True,
        license_active=True,
        license_status='active',
        workspace_id='workspace_1',
        instance_id_configured=True,
        license_key_configured=True,
        current_period_end=None,
        last_validated_at=stale_timestamp,
        last_checked_at=stale_timestamp,
        grace_until=None,
        last_error=None,
        license_server_base_url='https://app.automateki.de',
    )

    assert license_state.should_revalidate(snapshot) is True
