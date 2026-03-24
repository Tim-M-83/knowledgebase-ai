from __future__ import annotations

import logging
import socket
from dataclasses import replace

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.license_server import (
    LicenseServerError,
    RemoteLicenseStatus,
    activate_remote_license,
    create_checkout_url as create_remote_checkout_url,
    deactivate_remote_license,
    fetch_remote_status,
    reset_remote_activations,
    validate_remote_license,
)
from app.services.license_state import (
    LicenseSnapshot,
    clear_local_license_state,
    ensure_machine_fingerprint,
    ensure_workspace_id,
    get_instance_id,
    get_license_enabled,
    get_license_snapshot,
    get_stored_license_key,
    has_stored_license_key,
    persist_activation,
    persist_validation_result,
    record_server_unreachable,
    store_license_key,
    should_revalidate,
)


settings = get_settings()
logger = logging.getLogger(__name__)


def _hostname() -> str | None:
    try:
        return socket.gethostname().strip() or None
    except Exception:
        return None


def _company_name() -> str:
    return settings.license_company_name.strip() or settings.app_name


def _billing_email(fallback_email: str | None = None) -> str:
    configured = settings.license_billing_email.strip()
    if configured:
        return configured
    if fallback_email and fallback_email.strip():
        return fallback_email.strip()
    raise ValueError('LICENSE_BILLING_EMAIL is not configured.')


def start_checkout(
    db: Session,
    *,
    email: str | None = None,
    company_name: str | None = None,
) -> str:
    workspace_id = ensure_workspace_id(db)
    logger.info('License checkout requested workspace_id=%s', workspace_id)
    return create_remote_checkout_url(
        workspace_id=workspace_id,
        company_name=company_name or _company_name(),
        email=_billing_email(email),
    )


def _resolve_license_key(db: Session, license_key: str | None = None) -> str:
    if license_key is not None and license_key.strip():
        store_license_key(db, license_key)
        return license_key.strip()

    stored = get_stored_license_key(db)
    if stored:
        return stored

    raise ValueError('No license key is stored. Paste the Polar license key in Settings and activate this installation.')


def _record_runtime_validation_error(db: Session, exc: LicenseServerError) -> LicenseSnapshot:
    logger.warning('Runtime license validation failed: %s', exc)
    if exc.status_code >= 500:
        return record_server_unreachable(db, str(exc))
    return persist_validation_result(
        db,
        active=False,
        status='license_error',
        current_period_end=None,
        last_error=str(exc),
    )


def _with_remote_status(snapshot: LicenseSnapshot, remote_status: RemoteLicenseStatus) -> LicenseSnapshot:
    return replace(
        snapshot,
        current_period_end=snapshot.current_period_end or remote_status.current_period_end,
        remote_active_activation_count=remote_status.active_activation_count,
        remote_total_activation_count=remote_status.total_activation_count,
        activation_limit=remote_status.activation_limit,
    )


def _refresh_remote_status(db: Session, snapshot: LicenseSnapshot) -> LicenseSnapshot:
    workspace_id = snapshot.workspace_id or ensure_workspace_id(db)
    try:
        remote_status = fetch_remote_status(workspace_id=workspace_id)
    except LicenseServerError:
        return snapshot
    return _with_remote_status(snapshot, remote_status)


def activate_current_installation(
    db: Session,
    *,
    license_key: str | None = None,
    email: str | None = None,
) -> LicenseSnapshot:
    workspace_id = ensure_workspace_id(db)
    machine_fingerprint = ensure_machine_fingerprint(db)
    resolved_license_key = _resolve_license_key(db, license_key)
    response = activate_remote_license(
        workspace_id=workspace_id,
        company_name=_company_name(),
        email=_billing_email(email),
        license_key=resolved_license_key,
        machine_fingerprint=machine_fingerprint,
        hostname=_hostname(),
    )
    if not response.instance_id:
        raise LicenseServerError('License server did not return an activation instance ID.')
    snapshot = persist_activation(
        db,
        instance_id=response.instance_id,
        active=response.subscription_active,
        status=response.subscription_status,
        current_period_end=response.current_period_end,
    )
    logger.info(
        'License activated workspace_id=%s instance_id=%s status=%s',
        workspace_id,
        response.instance_id,
        response.subscription_status,
    )
    return _refresh_remote_status(db, snapshot)


def validate_current_license(db: Session) -> LicenseSnapshot:
    workspace_id = ensure_workspace_id(db)
    machine_fingerprint = ensure_machine_fingerprint(db)
    instance_id = get_instance_id(db)
    if not instance_id:
        raise ValueError('No local license activation was found. Activate this installation first.')
    resolved_license_key = _resolve_license_key(db)
    response = validate_remote_license(
        workspace_id=workspace_id,
        license_key=resolved_license_key,
        instance_id=instance_id,
        machine_fingerprint=machine_fingerprint,
    )
    if response.status == 'activation_not_found':
        logger.warning('Activation not found during validation. Attempting automatic recovery workspace_id=%s', workspace_id)
        activate_current_installation(db, license_key=resolved_license_key)
        refreshed_instance_id = get_instance_id(db)
        if not refreshed_instance_id:
            return clear_local_license_state(
                db,
                status='activation_not_found',
                last_error='Activation could not be recovered automatically.',
                clear_license_key=False,
            )
        response = validate_remote_license(
            workspace_id=workspace_id,
            license_key=resolved_license_key,
            instance_id=refreshed_instance_id,
            machine_fingerprint=machine_fingerprint,
        )
        if response.status == 'activation_not_found':
            logger.warning('Activation recovery failed workspace_id=%s', workspace_id)
            return clear_local_license_state(
                db,
                status='activation_not_found',
                last_error='Activation was not found after an automatic reactivation attempt.',
                clear_license_key=False,
            )

    snapshot = persist_validation_result(
        db,
        active=response.allowed,
        status=response.status,
        current_period_end=response.current_period_end,
    )
    logger.info(
        'License validated workspace_id=%s active=%s status=%s',
        workspace_id,
        response.allowed,
        response.status,
    )
    return _refresh_remote_status(db, snapshot)


def deactivate_current_license(db: Session) -> LicenseSnapshot:
    workspace_id = ensure_workspace_id(db)
    instance_id = get_instance_id(db)
    if not instance_id:
        raise ValueError('No active local license activation was found.')
    resolved_license_key = _resolve_license_key(db)

    deactivate_remote_license(
        workspace_id=workspace_id,
        license_key=resolved_license_key,
        instance_id=instance_id,
    )
    snapshot = clear_local_license_state(db, status='deactivated', clear_license_key=False)
    logger.info('License deactivated workspace_id=%s instance_id=%s', workspace_id, instance_id)
    return _refresh_remote_status(db, snapshot)


def reset_current_activations(db: Session) -> LicenseSnapshot:
    workspace_id = ensure_workspace_id(db)
    result = reset_remote_activations(workspace_id=workspace_id)
    snapshot = clear_local_license_state(db, status='activation_required', clear_license_key=False)
    logger.warning(
        'Workspace activations reset workspace_id=%s deactivated_count=%s',
        workspace_id,
        result.deactivated_count,
    )
    return replace(
        snapshot,
        current_period_end=result.current_period_end or snapshot.current_period_end,
        remote_active_activation_count=result.active_activation_count,
        remote_total_activation_count=result.total_activation_count,
        activation_limit=result.activation_limit,
    )


def validate_license_on_startup(db: Session) -> LicenseSnapshot:
    snapshot = get_license_snapshot(db)
    if not snapshot.instance_id_configured or not has_stored_license_key(db):
        return snapshot
    try:
        return validate_current_license(db)
    except LicenseServerError as exc:
        return _record_runtime_validation_error(db, exc)
    except ValueError:
        return snapshot


def ensure_runtime_license_snapshot(db: Session) -> LicenseSnapshot:
    snapshot = get_license_snapshot(db)
    if not get_license_enabled():
        return snapshot
    if not should_revalidate(snapshot):
        return snapshot
    try:
        return validate_current_license(db)
    except LicenseServerError as exc:
        return _record_runtime_validation_error(db, exc)
    except ValueError:
        return snapshot


def get_license_status_view(db: Session) -> LicenseSnapshot:
    snapshot = ensure_runtime_license_snapshot(db)
    return _refresh_remote_status(db, snapshot)


def has_runtime_license_access(db: Session) -> bool:
    if not get_license_enabled():
        return True
    snapshot = ensure_runtime_license_snapshot(db)
    return snapshot.license_active
