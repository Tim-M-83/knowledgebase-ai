import pytest

from app.services import provider_settings
from app.services.provider_settings import (
    KEY_OPENAI_API_KEY,
    KEY_OPENAI_API_KEY_DISABLED,
    clear_runtime_openai_api_key,
    get_runtime_openai_api_key,
    normalize_ollama_base_url,
    store_runtime_openai_api_key,
)


def test_normalize_ollama_base_url_trims_and_removes_trailing_slash():
    assert normalize_ollama_base_url('  http://localhost:11434/  ') == 'http://localhost:11434'


@pytest.mark.parametrize('value', ['localhost:11434', 'ftp://localhost:11434', 'http://'])
def test_normalize_ollama_base_url_rejects_invalid_urls(value: str):
    with pytest.raises(ValueError):
        normalize_ollama_base_url(value)


class DummySetting:
    def __init__(self, value: str):
        self.value = value


def test_get_runtime_openai_api_key_returns_empty_when_hard_disabled(monkeypatch):
    monkeypatch.setattr(provider_settings.settings, 'openai_api_key', 'sk-env-fallback', raising=False)

    def fake_get_setting(_db, key: str):
        if key == KEY_OPENAI_API_KEY_DISABLED:
            return DummySetting('true')
        return None

    monkeypatch.setattr(provider_settings, 'get_setting', fake_get_setting)

    assert get_runtime_openai_api_key(db=object()) == ''


def test_store_runtime_openai_api_key_clears_disabled_flag(monkeypatch):
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(provider_settings, 'encrypt_secret', lambda value: f'enc:{value}')
    monkeypatch.setattr(provider_settings, 'set_setting', lambda _db, key, value: calls.append((key, value)))

    store_runtime_openai_api_key(db=object(), api_key='sk-new')

    assert calls == [
        (KEY_OPENAI_API_KEY, 'enc:sk-new'),
        (KEY_OPENAI_API_KEY_DISABLED, 'false'),
    ]


def test_clear_runtime_openai_api_key_deletes_secret_and_sets_disabled(monkeypatch):
    deleted: list[str] = []
    writes: list[tuple[str, str]] = []
    monkeypatch.setattr(provider_settings, 'delete_setting', lambda _db, key: deleted.append(key))
    monkeypatch.setattr(provider_settings, 'set_setting', lambda _db, key, value: writes.append((key, value)))

    clear_runtime_openai_api_key(db=object())

    assert deleted == [KEY_OPENAI_API_KEY]
    assert writes == [(KEY_OPENAI_API_KEY_DISABLED, 'true')]
