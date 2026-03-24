from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting


KEY_EMAIL_HELPER_ENABLED = 'email_helper_enabled'


_TRUE_VALUES = {'1', 'true', 'yes', 'on'}
_FALSE_VALUES = {'0', 'false', 'no', 'off'}


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return default


def get_email_helper_enabled(db: Session | None, default: bool = True) -> bool:
    if db is None:
        return default
    item = db.query(AppSetting).filter(AppSetting.key == KEY_EMAIL_HELPER_ENABLED).first()
    if not item:
        return default
    return _parse_bool(item.value, default)
