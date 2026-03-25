from __future__ import annotations

import logging
import socket
from dataclasses import replace
from typing import Literal

from email_validator import EmailNotValidError, validate_email

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
    clear_runtime_billing_email,
    ensure_machine_fingerprint,
    ensure_workspace_id,
    get_instance_id,
    get_license_enabled,
    get_license_snapshot,
    get_runtime_billing_email,
    get_stored_license_key,
    has_stored_license_key,
    persist_activation,
    persist_validation_result,
    record_server_unreachable,
    store_runtime_billing_email,
    store_license_key,
    should_revalidate,
)


settings = get_settings()
logger = logging.getLogger(__name__)

DEMO_BILLING_EMAIL_DOMAINS = {
    'example.com',
    'example.org',
    'example.net',
    'localhost',
}
BillingEmailSource = Literal['saved', 'env', 'admin', 'none']


def _hostname() -> str | None:
    try:
        return socket.gethostname().strip() or None
    except Exception:
        return None


def _company_name() -> str:
    return settings.license_company_name.strip() or settings.app_name


def _normalize_billing_email(value: str | None) -> str | None:
    normalized = (value or '').strip()
    return normalized or None


def _validate_runtime_billing_email(email: str) -> str:
    normalized = email.strip()
    if not normalized:
        raise ValueError(
            'No billing email is configured. Save a real billing email in License & Subscription before continuing.'
        )

    try:
        validated = validate_email(normalized, check_deliverability=False)
    except EmailNotValidError as exc:
        raise ValueError(
            'Billing email is invalid. Save a real reachable billing email in License & Subscription before continuing.'
        ) from exc

    canonical = validated.normalized
    domain = canonical.rsplit('@', 1)[-1].strip().lower()
    if (
        domain in DEMO_BILLING_EMAIL_DOMAINS
        or domain.endswith('.local')
        or domain.endswith('.test')
    ):
        raise ValueError(
            'Billing email uses a demo/test domain and cannot be used for Polar checkout or activation. '
            'Save a real reachable billing email in License & Subscription before continuing.'
        )
    return canonical


def get_effective_billing_email(
    db: Session,
    *,
    fallback_email: str | None = None,
    validate_for_checkout: bool = False,
) -> tuple[str | None, BillingEmailSource]:
    runtime_email = _normalize_billing_email(get_runtime_billing_email(db))
    if runtime_email:
        return (
            _validate_runtime_billing_email(runtime_email) if validate_for_checkout else runtime_email,
            'saved',
        )

    configured_email = _normalize_billing_email(settings.license_billing_email)
    if configured_email:
        return (
            _validate_runtime_billing_email(configured_email) if validate_for_checkout else configured_email,
            'env',
        )

    admin_email = _normalize_billing_email(fallback_email)
    if admin_email:
        return (
            _validate_runtime_billing_email(admin_email) if validate_for_checkout else admin_email,
            'admin',
        )

    if validate_for_checkout:
        raise ValueError(
            'No billing email is configured. Save a real billing email in License & Subscription before continuing.'
        )
    return None, 'none'


def update_runtime_billing_email(db: Session, billing_email: str | None) -> tuple[str | None, BillingEmailSource]:
    normalized = _normalize_billing_email(billing_email)
    if normalized is None:
        clear_runtime_billing_email(db)
        return None, 'none'

    validated = _validate_runtime_billing_email(normalized)
    store_runtime_billing_email(db, validated)
    return validated, 'saved'


def start_checkout(
    db: Session,
    *,
    email: str | None = None,
    company_name: str | None = None,
) -> str:
    workspace_id = ensure_workspace_id(db)
    billing_email, _ = get_effective_billing_email(db, fallback_email=email, validate_for_checkout=True)
    logger.info('License checkout requested workspace_id=%s', workspace_id)
    return create_remote_checkout_url(
        workspace_id=workspace_id,
        company_name=company_name or _company_name(),
        email=billing_email,
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
    billing_email, _ = get_effective_billing_email(db, fallback_email=email, validate_for_checkout=True)
    response = activate_remote_license(
        workspace_id=workspace_id,
        company_name=_company_name(),
        email=billing_email,
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
