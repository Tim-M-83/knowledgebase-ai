import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rbac import require_roles
from app.core.security import validate_csrf
from app.db.session import get_db
from app.models.app_setting import AppSetting
from app.models.user import Role, User
from app.schemas.settings import (
    DataSettingsOut,
    DataSettingsUpdate,
    OllamaTestRequest,
    OllamaTestResponse,
    OpenAITestRequest,
    OpenAITestResponse,
    ProviderSettingsOut,
    ProviderSettingsUpdate,
)
from app.services.provider_settings import (
    AVAILABLE_RUNTIME_PROVIDERS,
    PROVIDER_OLLAMA,
    PROVIDER_OPENAI,
    clear_runtime_openai_api_key,
    get_runtime_ollama_base_url,
    get_runtime_ollama_chat_model,
    get_runtime_ollama_embeddings_model,
    get_runtime_openai_api_key,
    get_runtime_openai_chat_model,
    get_runtime_provider_pair,
    mask_openai_api_key,
    normalize_ollama_base_url,
    store_runtime_ollama_base_url,
    store_runtime_ollama_chat_model,
    store_runtime_ollama_embeddings_model,
    store_runtime_openai_api_key,
    store_runtime_openai_chat_model,
    store_runtime_provider_pair,
)
from app.services.feature_flags import KEY_EMAIL_HELPER_ENABLED, get_email_helper_enabled
from app.services.log_export import LogExportUnavailableError, build_support_log_export


router = APIRouter(prefix='/settings', tags=['settings'])
settings = get_settings()
logger = logging.getLogger(__name__)


KEY_RETENTION = 'retention_days'
KEY_MAX_UPLOAD = 'max_upload_mb'
FALLBACK_CHAT_MODELS = ['gpt-4o-mini', 'gpt-4.1-mini', 'gpt-4.1-nano']


def _get_or_create(db: Session, key: str, default: str) -> AppSetting:
    item = db.query(AppSetting).filter(AppSetting.key == key).first()
    if item:
        return item
    item = AppSetting(key=key, value=default)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _candidate_chat_models(preferred: str) -> list[str]:
    unique: list[str] = []
    for model in [preferred, *FALLBACK_CHAT_MODELS]:
        if model and model not in unique:
            unique.append(model)
    return unique


def _discover_openai_chat_models(client: OpenAI) -> list[str]:
    try:
        models = client.models.list()
    except Exception:
        return []

    candidates: list[str] = []
    for item in models.data:
        model_id = (item.id or '').strip()
        if not model_id:
            continue
        lower = model_id.lower()
        if any(token in lower for token in ['embedding', 'whisper', 'tts', 'image', 'moderation']):
            continue
        if lower.startswith('gpt') or lower.startswith('o'):
            candidates.append(model_id)
    return candidates


def _chat_probe(client: OpenAI, model: str) -> bool:
    try:
        client.responses.create(model=model, input='ping', max_output_tokens=8)
        return True
    except Exception:
        pass

    try:
        client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': 'ping'}],
            max_tokens=8,
            temperature=0.0,
        )
        return True
    except Exception:
        return False


def test_openai_endpoints(api_key: str, preferred_chat_model: str) -> OpenAITestResponse:
    client = OpenAI(api_key=api_key, timeout=30.0, max_retries=2)

    chat_ok = False
    embeddings_ok = False
    detail = 'OpenAI connection successful'
    selected_chat_model: str | None = None

    discovered_models = _discover_openai_chat_models(client)
    merged_candidates: list[str] = []
    for model in [*_candidate_chat_models(preferred_chat_model), *discovered_models]:
        if model and model not in merged_candidates:
            merged_candidates.append(model)

    for model in merged_candidates:
        if _chat_probe(client, model):
            chat_ok = True
            selected_chat_model = model
            if model != preferred_chat_model:
                detail = f'OpenAI connection successful. Using chat model: {model}'
            break

    if not chat_ok:
        detail = 'Chat endpoint check failed. Verify API key and available chat model.'

    try:
        client.embeddings.create(model=settings.openai_embeddings_model, input='ping')
        embeddings_ok = True
        if not chat_ok:
            detail = 'Embeddings endpoint succeeded, but no chat-capable model is available for this key/project.'
    except Exception:
        if chat_ok:
            detail = 'Embeddings endpoint check failed. Verify API key and embeddings model.'

    return OpenAITestResponse(
        ok=chat_ok and embeddings_ok,
        chat_endpoint_ok=chat_ok,
        embeddings_endpoint_ok=embeddings_ok,
        detail=detail,
        selected_chat_model=selected_chat_model,
    )


def _ollama_chat_probe(base_url: str, model: str) -> bool:
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': 'ping'}],
        'stream': False,
    }
    with httpx.Client(timeout=20.0) as client:
        response = client.post(f'{base_url}/api/chat', json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get('error'):
            raise ValueError(data['error'])
        return bool((data.get('message') or {}).get('content', '').strip())


def _ollama_embed_probe(base_url: str, model: str) -> tuple[bool, int | None]:
    with httpx.Client(timeout=20.0) as client:
        try:
            response = client.post(f'{base_url}/api/embed', json={'model': model, 'input': 'ping'})
            response.raise_for_status()
            data = response.json()
            embeddings = data.get('embeddings')
            if isinstance(embeddings, list) and embeddings:
                if isinstance(embeddings[0], list):
                    vector = embeddings[0]
                else:
                    vector = embeddings
                return True, len(vector)
        except Exception:
            pass

        response = client.post(f'{base_url}/api/embeddings', json={'model': model, 'prompt': 'ping'})
        response.raise_for_status()
        data = response.json()
        vector = data.get('embedding')
        if not isinstance(vector, list):
            raise ValueError('Ollama embeddings response did not include an embedding vector')
        return True, len(vector)


def test_ollama_endpoints(base_url: str, chat_model: str, embeddings_model: str) -> OllamaTestResponse:
    normalized_url = normalize_ollama_base_url(base_url)
    if not chat_model.strip():
        raise ValueError('Ollama chat model is required')
    if not embeddings_model.strip():
        raise ValueError('Ollama embeddings model is required')

    chat_ok = False
    embeddings_ok = False
    embedding_dim: int | None = None
    detail = 'Ollama connection successful'

    try:
        chat_ok = _ollama_chat_probe(normalized_url, chat_model.strip())
    except Exception as exc:
        detail = f'Ollama chat endpoint failed: {exc}'

    try:
        embeddings_ok, embedding_dim = _ollama_embed_probe(normalized_url, embeddings_model.strip())
        if chat_ok:
            detail = 'Ollama connection successful'
        else:
            detail = 'Ollama embeddings endpoint succeeded, but chat endpoint failed.'
    except Exception as exc:
        if chat_ok:
            detail = f'Ollama embeddings endpoint failed: {exc}'

    if embeddings_ok and embedding_dim and embedding_dim != settings.embedding_dimension:
        detail = (
            f'{detail} Embedding dimension is {embedding_dim}, while database vectors use '
            f'{settings.embedding_dimension}; vectors will be padded/truncated at runtime.'
        )

    return OllamaTestResponse(
        ok=chat_ok and embeddings_ok,
        chat_endpoint_ok=chat_ok,
        embeddings_endpoint_ok=embeddings_ok,
        detail=detail,
        embedding_dimension=embedding_dim,
    )


def _runtime_provider_payload(db: Session, warning: str | None = None) -> ProviderSettingsOut:
    llm_provider, embeddings_provider = get_runtime_provider_pair(db)
    key = get_runtime_openai_api_key(db)
    return ProviderSettingsOut(
        llm_provider=llm_provider,
        embeddings_provider=embeddings_provider,
        available_providers=AVAILABLE_RUNTIME_PROVIDERS,
        openai_chat_model=get_runtime_openai_chat_model(db),
        openai_embeddings_model=settings.openai_embeddings_model,
        openai_api_key_configured=bool(key),
        openai_api_key_masked=mask_openai_api_key(key),
        ollama_base_url=get_runtime_ollama_base_url(db),
        ollama_chat_model=get_runtime_ollama_chat_model(db),
        ollama_embeddings_model=get_runtime_ollama_embeddings_model(db),
        warning=warning,
    )


@router.get('/data', response_model=DataSettingsOut)
def get_data_settings(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin, Role.editor)),
):
    retention = _get_or_create(db, KEY_RETENTION, '365')
    max_upload = _get_or_create(db, KEY_MAX_UPLOAD, str(settings.max_upload_mb))
    _get_or_create(db, KEY_EMAIL_HELPER_ENABLED, 'true')
    return DataSettingsOut(
        retention_days=int(retention.value),
        max_upload_mb=int(max_upload.value),
        email_helper_enabled=get_email_helper_enabled(db),
    )


@router.put('/data', response_model=DataSettingsOut)
def update_data_settings(
    payload: DataSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin)),
):
    validate_csrf(request)
    retention = _get_or_create(db, KEY_RETENTION, str(payload.retention_days))
    max_upload = _get_or_create(db, KEY_MAX_UPLOAD, str(payload.max_upload_mb))
    email_helper = _get_or_create(db, KEY_EMAIL_HELPER_ENABLED, 'true')

    retention.value = str(payload.retention_days)
    max_upload.value = str(payload.max_upload_mb)
    email_helper.value = 'true' if payload.email_helper_enabled else 'false'
    db.commit()
    logger.info(
        'Data settings updated by user_id=%s retention_days=%s max_upload_mb=%s email_helper_enabled=%s',
        current_user.id,
        payload.retention_days,
        payload.max_upload_mb,
        payload.email_helper_enabled,
    )

    return DataSettingsOut(
        retention_days=payload.retention_days,
        max_upload_mb=payload.max_upload_mb,
        email_helper_enabled=payload.email_helper_enabled,
    )


@router.get('/providers', response_model=ProviderSettingsOut)
def get_provider_settings(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin, Role.editor)),
):
    return _runtime_provider_payload(db)


@router.put('/providers', response_model=ProviderSettingsOut)
def update_provider_settings(
    payload: ProviderSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin)),
):
    validate_csrf(request)

    current_llm, current_embeddings = get_runtime_provider_pair(db)
    llm_provider = (payload.llm_provider or '').strip().lower() or current_llm
    embeddings_provider = (payload.embeddings_provider or '').strip().lower() or current_embeddings
    if llm_provider not in AVAILABLE_RUNTIME_PROVIDERS or embeddings_provider not in AVAILABLE_RUNTIME_PROVIDERS:
        raise HTTPException(status_code=400, detail='Provider must be openai or ollama')
    if llm_provider != embeddings_provider:
        raise HTTPException(status_code=400, detail='LLM and embeddings provider must match for this deployment')

    warning_messages: list[str] = []

    if payload.openai_api_key is not None and payload.openai_api_key.strip():
        store_runtime_openai_api_key(db, payload.openai_api_key.strip())

    if payload.openai_chat_model is not None and payload.openai_chat_model.strip():
        store_runtime_openai_chat_model(db, payload.openai_chat_model.strip())

    if payload.ollama_base_url is not None:
        store_runtime_ollama_base_url(db, payload.ollama_base_url)
    if payload.ollama_chat_model is not None and payload.ollama_chat_model.strip():
        store_runtime_ollama_chat_model(db, payload.ollama_chat_model.strip())
    if payload.ollama_embeddings_model is not None and payload.ollama_embeddings_model.strip():
        store_runtime_ollama_embeddings_model(db, payload.ollama_embeddings_model.strip())

    if llm_provider == PROVIDER_OPENAI:
        openai_key = get_runtime_openai_api_key(db)
        openai_model = get_runtime_openai_chat_model(db)
        if not openai_key:
            warning_messages.append('OpenAI is selected but no OpenAI API key is configured.')
        else:
            test = test_openai_endpoints(openai_key, openai_model)
            if test.selected_chat_model:
                store_runtime_openai_chat_model(db, test.selected_chat_model)
            if not test.ok:
                warning_messages.append(test.detail)
    elif llm_provider == PROVIDER_OLLAMA:
        base_url = get_runtime_ollama_base_url(db)
        chat_model = get_runtime_ollama_chat_model(db)
        embeddings_model = get_runtime_ollama_embeddings_model(db)
        test = test_ollama_endpoints(base_url, chat_model, embeddings_model)
        if not test.ok:
            warning_messages.append(test.detail)
        elif test.detail and 'dimension' in test.detail.lower():
            warning_messages.append(test.detail)

    store_runtime_provider_pair(db, llm_provider=llm_provider, embeddings_provider=embeddings_provider)
    warning = ' | '.join(warning_messages) if warning_messages else None
    logger.info(
        'Provider settings updated by user_id=%s llm_provider=%s embeddings_provider=%s warning=%s',
        current_user.id,
        llm_provider,
        embeddings_provider,
        bool(warning),
    )
    return _runtime_provider_payload(db, warning=warning)


@router.delete('/providers/openai-key', response_model=ProviderSettingsOut)
def delete_openai_api_key(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin)),
):
    validate_csrf(request)
    clear_runtime_openai_api_key(db)
    logger.warning('OpenAI API key deleted by user_id=%s', current_user.id)
    return _runtime_provider_payload(db)


@router.post('/providers/test-openai', response_model=OpenAITestResponse)
def test_openai_connection(
    payload: OpenAITestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin, Role.editor)),
):
    api_key = (payload.openai_api_key or '').strip()
    if not api_key:
        api_key = get_runtime_openai_api_key(db)
    if not api_key:
        logger.warning('OpenAI connection test rejected for user_id=%s: no API key configured', current_user.id)
        raise HTTPException(status_code=400, detail='OpenAI API key is not configured')

    preferred_chat_model = get_runtime_openai_chat_model(db)
    result = test_openai_endpoints(api_key, preferred_chat_model)
    if not result.ok:
        logger.warning('OpenAI connection test failed for user_id=%s: %s', current_user.id, result.detail)
        raise HTTPException(status_code=400, detail=result.detail)
    logger.info('OpenAI connection test succeeded for user_id=%s', current_user.id)
    return result


@router.post('/providers/test-ollama', response_model=OllamaTestResponse)
def test_ollama_connection(
    payload: OllamaTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin, Role.editor)),
):
    try:
        base_url = payload.ollama_base_url or get_runtime_ollama_base_url(db)
        chat_model = payload.ollama_chat_model or get_runtime_ollama_chat_model(db)
        embeddings_model = payload.ollama_embeddings_model or get_runtime_ollama_embeddings_model(db)
        result = test_ollama_endpoints(base_url, chat_model, embeddings_model)
    except ValueError as exc:
        logger.warning('Ollama connection test failed for user_id=%s: %s', current_user.id, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        logger.warning('Ollama connection test failed for user_id=%s: %s', current_user.id, exc)
        raise HTTPException(status_code=400, detail=f'Ollama connection failed: {exc}') from exc

    if not result.ok:
        logger.warning('Ollama connection test failed for user_id=%s: %s', current_user.id, result.detail)
        raise HTTPException(status_code=400, detail=result.detail)
    logger.info('Ollama connection test succeeded for user_id=%s', current_user.id)
    return result


@router.get('/log-export')
def export_support_logs(
    current_user: User = Depends(require_roles(Role.admin)),
):
    try:
        archive, filename = build_support_log_export()
    except LogExportUnavailableError as exc:
        logger.warning('Support log export unavailable for user_id=%s: %s', current_user.id, exc)
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    logger.info('Support log export generated for user_id=%s', current_user.id)
    return Response(
        content=archive,
        media_type='application/zip',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Cache-Control': 'no-store',
        },
    )
