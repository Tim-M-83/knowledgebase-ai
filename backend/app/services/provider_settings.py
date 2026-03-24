from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.app_setting import AppSetting
from app.utils.crypto import decrypt_secret, encrypt_secret


settings = get_settings()

PROVIDER_OPENAI = 'openai'
PROVIDER_OLLAMA = 'ollama'
AVAILABLE_RUNTIME_PROVIDERS = [PROVIDER_OPENAI, PROVIDER_OLLAMA]

KEY_OPENAI_API_KEY = 'openai_api_key_encrypted'
KEY_OPENAI_API_KEY_DISABLED = 'openai_api_key_disabled'
KEY_OPENAI_CHAT_MODEL = 'openai_chat_model'
KEY_LLM_PROVIDER_RUNTIME = 'llm_provider_runtime'
KEY_EMBEDDINGS_PROVIDER_RUNTIME = 'embeddings_provider_runtime'
KEY_OLLAMA_BASE_URL = 'ollama_base_url'
KEY_OLLAMA_CHAT_MODEL = 'ollama_chat_model'
KEY_OLLAMA_EMBEDDINGS_MODEL = 'ollama_embeddings_model'


def get_setting(db: Session, key: str) -> AppSetting | None:
    return db.query(AppSetting).filter(AppSetting.key == key).first()


def set_setting(db: Session, key: str, value: str) -> AppSetting:
    item = get_setting(db, key)
    if item is None:
        item = AppSetting(key=key, value=value)
        db.add(item)
    else:
        item.value = value
    db.commit()
    db.refresh(item)
    return item


def delete_setting(db: Session, key: str) -> None:
    item = get_setting(db, key)
    if item is not None:
        db.delete(item)
        db.commit()


def _normalize_provider_value(value: str | None, default: str) -> str:
    candidate = (value or '').strip().lower()
    if candidate in AVAILABLE_RUNTIME_PROVIDERS:
        return candidate
    return default


def normalize_ollama_base_url(base_url: str) -> str:
    cleaned = (base_url or '').strip().rstrip('/')
    if not cleaned:
        raise ValueError('Ollama base URL is required')
    parsed = urlparse(cleaned)
    if parsed.scheme not in {'http', 'https'}:
        raise ValueError('Ollama base URL must start with http:// or https://')
    if not parsed.netloc:
        raise ValueError('Ollama base URL host is invalid')
    return cleaned


def get_runtime_provider_pair(db: Session | None) -> tuple[str, str]:
    if db is not None:
        llm_item = get_setting(db, KEY_LLM_PROVIDER_RUNTIME)
        emb_item = get_setting(db, KEY_EMBEDDINGS_PROVIDER_RUNTIME)
        llm_value = llm_item.value if llm_item else None
        emb_value = emb_item.value if emb_item else None
        return (
            _normalize_provider_value(llm_value, settings.llm_provider),
            _normalize_provider_value(emb_value, settings.embeddings_provider),
        )
    return (
        _normalize_provider_value(settings.llm_provider, settings.llm_provider),
        _normalize_provider_value(settings.embeddings_provider, settings.embeddings_provider),
    )


def store_runtime_provider_pair(db: Session, llm_provider: str, embeddings_provider: str) -> None:
    llm = _normalize_provider_value(llm_provider, settings.llm_provider)
    emb = _normalize_provider_value(embeddings_provider, settings.embeddings_provider)
    set_setting(db, KEY_LLM_PROVIDER_RUNTIME, llm)
    set_setting(db, KEY_EMBEDDINGS_PROVIDER_RUNTIME, emb)


def _read_bool_setting(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {'true', '1', 'yes', 'on'}:
        return True
    if normalized in {'false', '0', 'no', 'off'}:
        return False
    return default


def get_runtime_openai_api_key_disabled(db: Session | None) -> bool:
    if db is None:
        return False
    item = get_setting(db, KEY_OPENAI_API_KEY_DISABLED)
    if not item:
        return False
    return _read_bool_setting(item.value, default=False)


def get_runtime_openai_api_key(db: Session | None) -> str:
    if get_runtime_openai_api_key_disabled(db):
        return ''
    if db is not None:
        item = get_setting(db, KEY_OPENAI_API_KEY)
        if item and item.value:
            try:
                return decrypt_secret(item.value)
            except ValueError:
                return settings.openai_api_key
    return settings.openai_api_key


def store_runtime_openai_api_key(db: Session, api_key: str) -> None:
    encrypted = encrypt_secret(api_key.strip())
    set_setting(db, KEY_OPENAI_API_KEY, encrypted)
    set_setting(db, KEY_OPENAI_API_KEY_DISABLED, 'false')


def clear_runtime_openai_api_key(db: Session) -> None:
    delete_setting(db, KEY_OPENAI_API_KEY)
    set_setting(db, KEY_OPENAI_API_KEY_DISABLED, 'true')


def get_runtime_openai_chat_model(db: Session | None) -> str:
    if db is not None:
        item = get_setting(db, KEY_OPENAI_CHAT_MODEL)
        if item and item.value:
            return item.value.strip()
    return settings.openai_chat_model


def store_runtime_openai_chat_model(db: Session, model: str) -> None:
    set_setting(db, KEY_OPENAI_CHAT_MODEL, model.strip())


def get_runtime_ollama_base_url(db: Session | None) -> str:
    if db is not None:
        item = get_setting(db, KEY_OLLAMA_BASE_URL)
        if item and item.value:
            return normalize_ollama_base_url(item.value)
    return normalize_ollama_base_url(settings.ollama_base_url)


def store_runtime_ollama_base_url(db: Session, base_url: str) -> None:
    set_setting(db, KEY_OLLAMA_BASE_URL, normalize_ollama_base_url(base_url))


def get_runtime_ollama_chat_model(db: Session | None) -> str:
    if db is not None:
        item = get_setting(db, KEY_OLLAMA_CHAT_MODEL)
        if item and item.value:
            return item.value.strip()
    return settings.ollama_chat_model


def store_runtime_ollama_chat_model(db: Session, model: str) -> None:
    value = (model or '').strip()
    if not value:
        raise ValueError('Ollama chat model is required')
    set_setting(db, KEY_OLLAMA_CHAT_MODEL, value)


def get_runtime_ollama_embeddings_model(db: Session | None) -> str:
    if db is not None:
        item = get_setting(db, KEY_OLLAMA_EMBEDDINGS_MODEL)
        if item and item.value:
            return item.value.strip()
    return settings.ollama_embeddings_model


def store_runtime_ollama_embeddings_model(db: Session, model: str) -> None:
    value = (model or '').strip()
    if not value:
        raise ValueError('Ollama embeddings model is required')
    set_setting(db, KEY_OLLAMA_EMBEDDINGS_MODEL, value)


def mask_openai_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    if len(api_key) <= 10:
        return '*' * len(api_key)
    return f"{api_key[:6]}{'*' * (len(api_key) - 10)}{api_key[-4:]}"
