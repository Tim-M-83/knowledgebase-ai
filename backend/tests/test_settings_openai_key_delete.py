from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes import settings
from app.core.rbac import require_roles
from app.models.user import Role


def test_delete_openai_key_calls_clear_and_returns_updated_payload(monkeypatch):
    called = {'csrf': False, 'cleared': False}
    db = object()
    expected_payload = {
        'llm_provider': 'openai',
        'embeddings_provider': 'openai',
        'available_providers': ['openai', 'ollama'],
        'openai_chat_model': 'gpt-4.1-mini',
        'openai_embeddings_model': 'text-embedding-3-small',
        'openai_api_key_configured': False,
        'openai_api_key_masked': None,
        'ollama_base_url': 'http://host.docker.internal:11434',
        'ollama_chat_model': 'llama3.1:8b',
        'ollama_embeddings_model': 'nomic-embed-text',
        'warning': None,
    }

    def fake_validate_csrf(request):
        assert request is not None
        called['csrf'] = True

    def fake_clear_runtime_openai_api_key(input_db):
        assert input_db is db
        called['cleared'] = True

    monkeypatch.setattr(settings, 'validate_csrf', fake_validate_csrf)
    monkeypatch.setattr(settings, 'clear_runtime_openai_api_key', fake_clear_runtime_openai_api_key)
    monkeypatch.setattr(settings, '_runtime_provider_payload', lambda input_db: expected_payload)

    out = settings.delete_openai_api_key(
        request=object(),
        db=db,
        current_user=SimpleNamespace(id=1, role=Role.admin),
    )

    assert called == {'csrf': True, 'cleared': True}
    assert out == expected_payload


def test_delete_openai_key_rejects_invalid_csrf(monkeypatch):
    def fake_validate_csrf(_request):
        raise HTTPException(status_code=403, detail='Invalid CSRF token')

    monkeypatch.setattr(settings, 'validate_csrf', fake_validate_csrf)

    with pytest.raises(HTTPException) as exc:
        settings.delete_openai_api_key(
            request=object(),
            db=object(),
            current_user=SimpleNamespace(id=1, role=Role.admin),
        )

    assert exc.value.status_code == 403
    assert 'CSRF' in str(exc.value.detail)


def test_delete_openai_key_endpoint_is_admin_only():
    checker = require_roles(Role.admin)
    with pytest.raises(HTTPException) as exc:
        checker(current_user=SimpleNamespace(role=Role.editor))
    assert exc.value.status_code == 403
