import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.rbac import require_roles
from app.core.security import get_current_user, validate_csrf
from app.db.session import get_db
from app.models.user import Role, User
from app.schemas.license import LicenseActivateIn, LicenseBillingEmailIn, LicenseStatusOut, LicenseUrlOut
from app.services.license_manager import (
    LicenseServerError,
    activate_current_installation,
    deactivate_current_license,
    get_effective_billing_email,
    get_license_status_view,
    reset_current_activations,
    start_checkout,
    update_runtime_billing_email,
    validate_current_license,
)
from app.services.license_state import LicenseSnapshot


router = APIRouter(prefix='/license', tags=['license'])
logger = logging.getLogger(__name__)


def _to_status(snapshot: LicenseSnapshot, *, db: Session, current_user: User) -> LicenseStatusOut:
    fallback_email = current_user.email if current_user.role == Role.admin else None
    billing_email, billing_email_source = get_effective_billing_email(db, fallback_email=fallback_email)
    return LicenseStatusOut(
        license_enabled=snapshot.license_enabled,
        license_active=snapshot.license_active,
        license_status=snapshot.license_status,
        workspace_id=snapshot.workspace_id,
        instance_id_configured=snapshot.instance_id_configured,
        license_key_configured=snapshot.license_key_configured,
        current_period_end=snapshot.current_period_end,
        last_validated_at=snapshot.last_validated_at,
        grace_until=snapshot.grace_until,
        last_error=snapshot.last_error,
        license_server_base_url=snapshot.license_server_base_url,
        remote_active_activation_count=snapshot.remote_active_activation_count,
        remote_total_activation_count=snapshot.remote_total_activation_count,
        activation_limit=snapshot.activation_limit,
        billing_email=billing_email,
        billing_email_source=billing_email_source,
    )


def _raise_license_error(exc: Exception) -> None:
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(exc, LicenseServerError):
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    raise exc


@router.get('/status', response_model=LicenseStatusOut)
def get_license_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _to_status(get_license_status_view(db), db=db, current_user=current_user)


@router.post('/checkout', response_model=LicenseUrlOut)
def create_checkout(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin)),
):
    validate_csrf(request)
    try:
        url = start_checkout(db, email=current_user.email)
    except Exception as exc:
        logger.warning('License checkout failed for user_id=%s: %s', current_user.id, exc)
        _raise_license_error(exc)
    logger.info('License checkout created for user_id=%s', current_user.id)
    return LicenseUrlOut(url=url)


@router.put('/billing-email', response_model=LicenseStatusOut)
def update_billing_email(
    payload: LicenseBillingEmailIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin)),
):
    validate_csrf(request)
    try:
        update_runtime_billing_email(db, payload.billing_email)
        snapshot = get_license_status_view(db)
    except Exception as exc:
        logger.warning('License billing email update failed for user_id=%s: %s', current_user.id, exc)
        _raise_license_error(exc)
    logger.info('License billing email updated for user_id=%s', current_user.id)
    return _to_status(snapshot, db=db, current_user=current_user)


@router.post('/activate', response_model=LicenseStatusOut)
def activate(
    payload: LicenseActivateIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin)),
):
    validate_csrf(request)
    try:
        snapshot = activate_current_installation(db, license_key=payload.license_key, email=current_user.email)
    except Exception as exc:
        logger.warning('License activation failed for user_id=%s: %s', current_user.id, exc)
        _raise_license_error(exc)
    logger.info('License activation completed for user_id=%s status=%s', current_user.id, snapshot.license_status)
    return _to_status(snapshot, db=db, current_user=current_user)


@router.post('/validate', response_model=LicenseStatusOut)
def validate(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin)),
):
    validate_csrf(request)
    try:
        snapshot = validate_current_license(db)
    except Exception as exc:
        logger.warning('License validation failed: %s', exc)
        _raise_license_error(exc)
    logger.info('License validation completed status=%s', snapshot.license_status)
    return _to_status(snapshot, db=db, current_user=current_user)


@router.post('/deactivate', response_model=LicenseStatusOut)
def deactivate(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin)),
):
    validate_csrf(request)
    try:
        snapshot = deactivate_current_license(db)
    except Exception as exc:
        logger.warning('License deactivation failed: %s', exc)
        _raise_license_error(exc)
    logger.info('License deactivation completed status=%s', snapshot.license_status)
    return _to_status(snapshot, db=db, current_user=current_user)


@router.post('/reset-activations', response_model=LicenseStatusOut)
def reset_activations(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin)),
):
    validate_csrf(request)
    try:
        snapshot = reset_current_activations(db)
    except Exception as exc:
        logger.warning('License activation reset failed: %s', exc)
        _raise_license_error(exc)
    logger.info('License activations reset completed status=%s', snapshot.license_status)
    return _to_status(snapshot, db=db, current_user=current_user)
