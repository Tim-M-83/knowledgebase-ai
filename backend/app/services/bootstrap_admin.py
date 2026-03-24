from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import Role, User


logger = logging.getLogger(__name__)

BOOTSTRAP_ADMIN_EMAIL = 'admin@local'


@dataclass
class BootstrapAdminCredentials:
    email: str
    password: str


def generate_bootstrap_password() -> str:
    return secrets.token_urlsafe(18)


def ensure_bootstrap_admin(db: Session) -> BootstrapAdminCredentials | None:
    existing_admin = db.query(User).filter(User.role == Role.admin).first()
    if existing_admin is not None:
        return None

    password = generate_bootstrap_password()
    user = User(
        email=BOOTSTRAP_ADMIN_EMAIL,
        password_hash=get_password_hash(password),
        role=Role.admin,
        must_change_credentials=True,
        is_bootstrap_admin=True,
    )
    db.add(user)
    db.commit()

    return BootstrapAdminCredentials(email=BOOTSTRAP_ADMIN_EMAIL, password=password)


def log_bootstrap_admin(credentials: BootstrapAdminCredentials) -> None:
    logger.warning(
        '\n%s\nBootstrap admin created for this installation.\n'
        'Email: %s\n'
        'Password: %s\n'
        'Sign in immediately and change both email and password in Settings.\n'
        'These credentials are only shown once during the first bootstrap.\n%s',
        '=' * 72,
        credentials.email,
        credentials.password,
        '=' * 72,
    )
