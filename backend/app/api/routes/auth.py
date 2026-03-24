import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_csrf_token,
    get_password_hash,
    get_current_user,
    validate_csrf,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import CredentialUpdateRequest, CredentialUpdateResponse, LoginRequest, MeResponse
from app.services.feature_flags import get_email_helper_enabled
from app.services.license_manager import ensure_runtime_license_snapshot


router = APIRouter(prefix='/auth', tags=['auth'])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post('/login', response_model=MeResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        logger.warning('Authentication failed: invalid credentials.')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')

    token = create_access_token(str(user.id))
    csrf = generate_csrf_token()

    response.set_cookie(
        key=settings.jwt_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite='lax',
        max_age=settings.jwt_expire_hours * 3600,
        path='/',
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf,
        httponly=False,
        secure=settings.cookie_secure,
        samesite='lax',
        max_age=settings.jwt_expire_hours * 3600,
        path='/',
    )

    license_snapshot = ensure_runtime_license_snapshot(db)
    logger.info('Authentication succeeded for user_id=%s role=%s', user.id, user.role.value)

    return MeResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        department_id=user.department_id,
        email_helper_enabled=get_email_helper_enabled(db),
        license_enabled=license_snapshot.license_enabled,
        license_active=license_snapshot.license_active,
        license_status=license_snapshot.license_status,
        license_grace_until=license_snapshot.grace_until,
        must_change_credentials=user.must_change_credentials,
    )


@router.post('/logout')
def logout(response: Response):
    response.delete_cookie(settings.jwt_cookie_name, path='/')
    response.delete_cookie(settings.csrf_cookie_name, path='/')
    return {'message': 'Logged out'}


@router.get('/me', response_model=MeResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    license_snapshot = ensure_runtime_license_snapshot(db)
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        department_id=current_user.department_id,
        email_helper_enabled=get_email_helper_enabled(db),
        license_enabled=license_snapshot.license_enabled,
        license_active=license_snapshot.license_active,
        license_status=license_snapshot.license_status,
        license_grace_until=license_snapshot.grace_until,
        must_change_credentials=current_user.must_change_credentials,
    )


@router.put('/me/credentials', response_model=CredentialUpdateResponse)
def update_my_credentials(
    payload: CredentialUpdateRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_csrf(request)

    normalized_email: str | None = None
    normalized_password: str | None = None
    normalized_current_password = payload.current_password.strip() if payload.current_password is not None else None

    if not current_user.must_change_credentials:
        if not normalized_current_password:
            logger.warning('Credential update rejected for user_id=%s: current password missing', current_user.id)
            raise HTTPException(status_code=400, detail='current_password is required')
        if not verify_password(normalized_current_password, current_user.password_hash):
            logger.warning('Credential update rejected for user_id=%s: current password invalid', current_user.id)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Current password is incorrect')

    if payload.new_email is not None:
        normalized_email = str(payload.new_email).strip()
        if not normalized_email:
            raise HTTPException(status_code=400, detail='new_email must not be empty')

    if payload.new_password is not None:
        normalized_password = payload.new_password.strip()
        if not normalized_password:
            raise HTTPException(status_code=400, detail='new_password must not be empty')

    if normalized_email is None and normalized_password is None:
        raise HTTPException(status_code=400, detail='At least one of new_email or new_password must be provided')

    if current_user.must_change_credentials and (normalized_email is None or normalized_password is None):
        raise HTTPException(
            status_code=400,
            detail='Bootstrap admin must update both email and password before continuing',
        )

    if normalized_email is not None:
        existing = (
            db.query(User.id)
            .filter(func.lower(User.email) == normalized_email.lower(), User.id != current_user.id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail='Email already exists')
        current_user.email = normalized_email

    if normalized_password is not None:
        current_user.password_hash = get_password_hash(normalized_password)

    current_user.must_change_credentials = False
    current_user.is_bootstrap_admin = False

    db.commit()
    logger.info('Credentials updated for user_id=%s', current_user.id)
    response.delete_cookie(settings.jwt_cookie_name, path='/')
    response.delete_cookie(settings.csrf_cookie_name, path='/')
    return CredentialUpdateResponse(message='Credentials updated. Please sign in again.')
