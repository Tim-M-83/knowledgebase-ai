from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.app_setting import AppSetting
from app.utils.crypto import decrypt_secret, encrypt_secret


settings = get_settings()

KEY_LICENSE_WORKSPACE_ID = 'license_workspace_id'
KEY_LICENSE_MACHINE_FINGERPRINT = 'license_machine_fingerprint'
KEY_LICENSE_BILLING_EMAIL_RUNTIME = 'license_billing_email_runtime'
KEY_LICENSE_KEY_ENCRYPTED = 'license_key_encrypted'
KEY_LICENSE_INSTANCE_ID = 'license_instance_id'
KEY_LICENSE_STATUS = 'license_status'
KEY_LICENSE_ACTIVE = 'license_active'
KEY_LICENSE_CURRENT_PERIOD_END = 'license_current_period_end'
KEY_LICENSE_LAST_VALIDATED_AT = 'license_last_validated_at'
KEY_LICENSE_LAST_CHECKED_AT = 'license_last_checked_at'
KEY_LICENSE_GRACE_UNTIL = 'license_grace_until'
KEY_LICENSE_LAST_ERROR = 'license_last_error'


@dataclass
class LicenseSnapshot:
    license_enabled: bool
    license_active: bool
    license_status: str | None
    workspace_id: str | None
    instance_id_configured: bool
    license_key_configured: bool
    current_period_end: str | None
    last_validated_at: str | None
    last_checked_at: str | None
    grace_until: str | None
    last_error: str | None
    license_server_base_url: str
    remote_active_activation_count: int | None = None
    remote_total_activation_count: int | None = None
    activation_limit: int | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off'}:
        return False
    return default


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)
    except ValueError:
        return None


def _get_setting(db: Session, key: str) -> AppSetting | None:
    return db.query(AppSetting).filter(AppSetting.key == key).first()


def _get_setting_value(db: Session, key: str) -> str | None:
    item = _get_setting(db, key)
    if not item:
        return None
    value = item.value.strip()
    return value or None


def _upsert(db: Session, key: str, value: str) -> None:
    item = _get_setting(db, key)
    if item is None:
        db.add(AppSetting(key=key, value=value))
    else:
        item.value = value


def _set_or_delete(db: Session, key: str, value: str | None) -> None:
    if value is None:
        item = _get_setting(db, key)
        if item is not None:
            db.delete(item)
        return
    _upsert(db, key, value)


def get_license_enabled() -> bool:
    return bool(settings.license_enforcement_enabled)


def ensure_workspace_id(db: Session) -> str:
    configured = settings.license_workspace_id.strip()
    if configured:
        existing = _get_setting_value(db, KEY_LICENSE_WORKSPACE_ID)
        if existing != configured:
            _upsert(db, KEY_LICENSE_WORKSPACE_ID, configured)
            db.commit()
        return configured

    existing = _get_setting_value(db, KEY_LICENSE_WORKSPACE_ID)
    if existing:
        return existing
    generated = f'workspace-{uuid4().hex}'
    _upsert(db, KEY_LICENSE_WORKSPACE_ID, generated)
    db.commit()
    return generated


def ensure_machine_fingerprint(db: Session) -> str:
    existing = _get_setting_value(db, KEY_LICENSE_MACHINE_FINGERPRINT)
    if existing:
        return existing
    generated = f'machine-{uuid4().hex}'
    _upsert(db, KEY_LICENSE_MACHINE_FINGERPRINT, generated)
    db.commit()
    return generated


def get_runtime_billing_email(db: Session) -> str | None:
    return _get_setting_value(db, KEY_LICENSE_BILLING_EMAIL_RUNTIME)


def store_runtime_billing_email(db: Session, billing_email: str) -> None:
    normalized = billing_email.strip()
    if not normalized:
        raise ValueError('billing_email must not be empty')
    _upsert(db, KEY_LICENSE_BILLING_EMAIL_RUNTIME, normalized)
    db.commit()


def clear_runtime_billing_email(db: Session) -> None:
    _set_or_delete(db, KEY_LICENSE_BILLING_EMAIL_RUNTIME, None)
    db.commit()


def get_instance_id(db: Session) -> str | None:
    return _get_setting_value(db, KEY_LICENSE_INSTANCE_ID)


def get_stored_license_key(db: Session) -> str | None:
    encrypted = _get_setting_value(db, KEY_LICENSE_KEY_ENCRYPTED)
    if not encrypted:
        return None
    try:
        return decrypt_secret(encrypted)
    except ValueError:
        return None


def has_stored_license_key(db: Session) -> bool:
    return bool(get_stored_license_key(db))


def store_license_key(db: Session, license_key: str) -> None:
    normalized = license_key.strip()
    if not normalized:
        raise ValueError('license_key must not be empty')
    _upsert(db, KEY_LICENSE_KEY_ENCRYPTED, encrypt_secret(normalized))
    db.commit()


def clear_stored_license_key(db: Session) -> None:
    _set_or_delete(db, KEY_LICENSE_KEY_ENCRYPTED, None)
    db.commit()


def _grace_is_valid(grace_until: str | None) -> bool:
    parsed = _parse_datetime(grace_until)
    return bool(parsed and parsed > _now())


def get_license_snapshot(db: Session) -> LicenseSnapshot:
    workspace_id = ensure_workspace_id(db)
    raw_status = _get_setting_value(db, KEY_LICENSE_STATUS)
    raw_active = _parse_bool(_get_setting_value(db, KEY_LICENSE_ACTIVE), default=False)
    grace_until = _get_setting_value(db, KEY_LICENSE_GRACE_UNTIL)
    instance_id = get_instance_id(db)
    license_key_configured = has_stored_license_key(db)
    grace_active = _grace_is_valid(grace_until)

    license_active = raw_active or grace_active
    license_status = raw_status
    if not license_status:
        if not instance_id:
            license_status = 'activation_required'
        elif grace_active:
            license_status = 'grace'
        elif license_active:
            license_status = 'active'
        else:
            license_status = 'inactive'

    return LicenseSnapshot(
        license_enabled=get_license_enabled(),
        license_active=license_active,
        license_status=license_status,
        workspace_id=workspace_id,
        instance_id_configured=bool(instance_id),
        license_key_configured=license_key_configured,
        current_period_end=_get_setting_value(db, KEY_LICENSE_CURRENT_PERIOD_END),
        last_validated_at=_get_setting_value(db, KEY_LICENSE_LAST_VALIDATED_AT),
        last_checked_at=_get_setting_value(db, KEY_LICENSE_LAST_CHECKED_AT),
        grace_until=grace_until,
        last_error=_get_setting_value(db, KEY_LICENSE_LAST_ERROR),
        license_server_base_url=settings.license_server_base_url.strip(),
    )


def should_revalidate(snapshot: LicenseSnapshot) -> bool:
    if not snapshot.instance_id_configured:
        return False
    reference = _parse_datetime(snapshot.last_checked_at or snapshot.last_validated_at)
    if reference is None:
        return True
    delta = _now() - reference
    return delta >= timedelta(minutes=settings.effective_license_validation_minutes)


def persist_activation(
    db: Session,
    *,
    instance_id: str,
    active: bool,
    status: str | None,
    current_period_end: str | None,
) -> LicenseSnapshot:
    now_iso = _now_iso()
    _upsert(db, KEY_LICENSE_INSTANCE_ID, instance_id.strip())
    _upsert(db, KEY_LICENSE_ACTIVE, 'true' if active else 'false')
    _upsert(db, KEY_LICENSE_STATUS, (status or ('active' if active else 'inactive')).strip().lower())
    _set_or_delete(db, KEY_LICENSE_CURRENT_PERIOD_END, current_period_end.strip() if current_period_end else None)
    _upsert(db, KEY_LICENSE_LAST_CHECKED_AT, now_iso)
    if active:
        _upsert(db, KEY_LICENSE_LAST_VALIDATED_AT, now_iso)
        _upsert(
            db,
            KEY_LICENSE_GRACE_UNTIL,
            (_now() + timedelta(hours=settings.effective_license_grace_hours)).isoformat(),
        )
    else:
        _set_or_delete(db, KEY_LICENSE_GRACE_UNTIL, None)
    _set_or_delete(db, KEY_LICENSE_LAST_ERROR, None)
    db.commit()
    return get_license_snapshot(db)


def persist_validation_result(
    db: Session,
    *,
    active: bool,
    status: str | None,
    current_period_end: str | None,
    last_error: str | None = None,
) -> LicenseSnapshot:
    now_iso = _now_iso()

    _upsert(db, KEY_LICENSE_ACTIVE, 'true' if active else 'false')
    _upsert(db, KEY_LICENSE_STATUS, (status or ('active' if active else 'inactive')).strip().lower())
    _set_or_delete(db, KEY_LICENSE_CURRENT_PERIOD_END, current_period_end.strip() if current_period_end else None)
    _upsert(db, KEY_LICENSE_LAST_CHECKED_AT, now_iso)
    if active:
        _upsert(db, KEY_LICENSE_LAST_VALIDATED_AT, now_iso)
        _upsert(
            db,
            KEY_LICENSE_GRACE_UNTIL,
            (_now() + timedelta(hours=settings.effective_license_grace_hours)).isoformat(),
        )
        _set_or_delete(db, KEY_LICENSE_LAST_ERROR, None)
    else:
        _set_or_delete(db, KEY_LICENSE_GRACE_UNTIL, None)
        _set_or_delete(db, KEY_LICENSE_LAST_ERROR, last_error.strip() if last_error else None)
    db.commit()
    return get_license_snapshot(db)


def record_server_unreachable(db: Session, message: str) -> LicenseSnapshot:
    snapshot = get_license_snapshot(db)
    _upsert(db, KEY_LICENSE_LAST_CHECKED_AT, _now_iso())
    _upsert(db, KEY_LICENSE_ACTIVE, 'false')
    _upsert(db, KEY_LICENSE_STATUS, 'grace' if _grace_is_valid(snapshot.grace_until) else 'unreachable')
    _upsert(db, KEY_LICENSE_LAST_ERROR, message.strip() or 'License server unavailable.')
    db.commit()
    return get_license_snapshot(db)


def clear_local_license_state(
    db: Session,
    *,
    status: str = 'deactivated',
    last_error: str | None = None,
    clear_license_key: bool = False,
) -> LicenseSnapshot:
    if clear_license_key:
        _set_or_delete(db, KEY_LICENSE_KEY_ENCRYPTED, None)
    _set_or_delete(db, KEY_LICENSE_INSTANCE_ID, None)
    _set_or_delete(db, KEY_LICENSE_GRACE_UNTIL, None)
    _set_or_delete(db, KEY_LICENSE_CURRENT_PERIOD_END, None)
    _upsert(db, KEY_LICENSE_ACTIVE, 'false')
    _upsert(db, KEY_LICENSE_STATUS, status.strip().lower())
    _upsert(db, KEY_LICENSE_LAST_CHECKED_AT, _now_iso())
    _set_or_delete(db, KEY_LICENSE_LAST_ERROR, last_error.strip() if last_error else None)
    db.commit()
    return get_license_snapshot(db)
