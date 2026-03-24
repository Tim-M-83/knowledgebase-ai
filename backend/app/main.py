from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
import httpx
import redis
import logging

from app.api.routes import (
    ai_document_summarizer,
    auth,
    chat,
    dashboard,
    departments,
    documents,
    email_helper,
    folders,
    license,
    personal_notes,
    settings as settings_routes,
    tags,
    users,
)
from app.core.config import get_settings
from app.core.logging_setup import configure_app_logging
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import Role, User
from app.services.bootstrap_admin import ensure_bootstrap_admin, log_bootstrap_admin
from app.services.license_manager import has_runtime_license_access, validate_license_on_startup
from app.services.provider_settings import (
    PROVIDER_OLLAMA,
    get_runtime_ollama_base_url,
    get_runtime_ollama_chat_model,
    get_runtime_ollama_embeddings_model,
    get_runtime_openai_api_key,
    get_runtime_openai_chat_model,
    get_runtime_provider_pair,
)


settings = get_settings()
configure_app_logging('api')
app = FastAPI(title=settings.app_name)
logger = logging.getLogger(__name__)

_LICENSE_GUARD_ALLOW_PREFIXES = (
    '/license',
    '/docs',
    '/redoc',
)
_LICENSE_GUARD_ALLOW_EXACT = (
    '/auth/login',
    '/auth/logout',
    '/auth/me',
    '/auth/me/credentials',
    '/health',
    '/openapi.json',
)
_BOOTSTRAP_GUARD_ALLOW_EXACT = (
    '/auth/login',
    '/auth/logout',
    '/auth/me',
    '/auth/me/credentials',
    '/health',
    '/openapi.json',
)
_BOOTSTRAP_GUARD_ALLOW_PREFIXES = (
    '/docs',
    '/redoc',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.exception_handler(ValueError)
def value_error_handler(_: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={'detail': str(exc)})


@app.exception_handler(Exception)
def generic_error_handler(_: Request, exc: Exception):
    logger.exception('Unhandled error: %s', exc)
    return JSONResponse(status_code=500, content={'detail': 'Internal server error'})


@app.on_event('startup')
def bootstrap_admin_on_startup() -> None:
    db = SessionLocal()
    try:
        credentials = ensure_bootstrap_admin(db)
    finally:
        db.close()

    if credentials is not None:
        log_bootstrap_admin(credentials)


@app.on_event('startup')
def refresh_license_on_startup() -> None:
    db = SessionLocal()
    try:
        validate_license_on_startup(db)
    except Exception as exc:
        logger.exception('Startup license refresh failed: %s', exc)
    finally:
        db.close()


@app.middleware('http')
async def bootstrap_credential_guard(request: Request, call_next):
    path = request.url.path
    if path in _BOOTSTRAP_GUARD_ALLOW_EXACT or path.startswith(_BOOTSTRAP_GUARD_ALLOW_PREFIXES):
        return await call_next(request)

    token = request.cookies.get(settings.jwt_cookie_name)
    if not token:
        return await call_next(request)

    try:
        payload = decode_access_token(token)
        subject = payload.get('sub')
        user_id = int(subject) if subject is not None else None
    except Exception:
        return await call_next(request)

    if user_id is None:
        return await call_next(request)

    db = None
    try:
        db = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.must_change_credentials:
            return JSONResponse(
                status_code=403,
                content={'detail': 'Initial security setup required. Update email and password in Settings.'},
            )
        return await call_next(request)
    except Exception as exc:
        logger.exception('Bootstrap credential guard failed: %s', exc)
        return await call_next(request)
    finally:
        if db is not None:
            db.close()


@app.middleware('http')
async def license_enforcement_guard(request: Request, call_next):
    path = request.url.path
    if not settings.license_enforcement_enabled:
        return await call_next(request)
    if path in _LICENSE_GUARD_ALLOW_EXACT or path.startswith(_LICENSE_GUARD_ALLOW_PREFIXES):
        return await call_next(request)

    token = request.cookies.get(settings.jwt_cookie_name)
    if not token:
        return await call_next(request)

    try:
        payload = decode_access_token(token)
        subject = payload.get('sub')
        user_id = int(subject) if subject is not None else None
    except Exception:
        return await call_next(request)

    if user_id is None:
        return await call_next(request)

    db = None
    try:
        db = SessionLocal()

        if path.startswith('/settings'):
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.role == Role.admin:
                return await call_next(request)

        if has_runtime_license_access(db):
            return await call_next(request)

        return JSONResponse(
            status_code=403,
            content={'detail': 'License inactive. Activate or validate the workspace license to continue.'},
        )
    except Exception as exc:
        logger.exception('License guard check failed: %s', exc)
        return await call_next(request)
    finally:
        if db is not None:
            db.close()


@app.get('/health')
def health():
    db_ok = False
    redis_ok = False
    openai_key_configured = bool(settings.openai_api_key)
    openai_chat_model = settings.openai_chat_model
    llm_provider = settings.llm_provider
    embeddings_provider = settings.embeddings_provider
    ollama_base_url = settings.ollama_base_url
    ollama_chat_model = settings.ollama_chat_model
    ollama_embeddings_model = settings.ollama_embeddings_model
    ollama_reachable: bool | None = None
    db = None
    try:
        db = SessionLocal()
        db.execute(text('SELECT 1'))
        llm_provider, embeddings_provider = get_runtime_provider_pair(db)
        openai_key_configured = bool(get_runtime_openai_api_key(db))
        openai_chat_model = get_runtime_openai_chat_model(db)
        ollama_base_url = get_runtime_ollama_base_url(db)
        ollama_chat_model = get_runtime_ollama_chat_model(db)
        ollama_embeddings_model = get_runtime_ollama_embeddings_model(db)
        db_ok = True
    except Exception:
        db_ok = False
    finally:
        if db is not None:
            db.close()

    try:
        client = redis.Redis.from_url(settings.redis_url)
        redis_ok = bool(client.ping())
    except Exception:
        redis_ok = False

    if llm_provider == PROVIDER_OLLAMA or embeddings_provider == PROVIDER_OLLAMA:
        try:
            with httpx.Client(timeout=3.0) as client:
                response = client.post(
                    f'{ollama_base_url.rstrip("/")}/api/embed',
                    json={'model': ollama_embeddings_model, 'input': 'ping'},
                )
                if response.is_success:
                    ollama_reachable = True
                else:
                    ollama_reachable = False
        except Exception:
            ollama_reachable = False

    return {
        'status': 'ok' if db_ok and redis_ok else 'degraded',
        'provider': {
            'llm': llm_provider,
            'embeddings': embeddings_provider,
            'openai_chat_model': openai_chat_model,
            'openai_embeddings_model': settings.openai_embeddings_model,
            'openai_api_key_configured': openai_key_configured,
            'ollama_base_url': ollama_base_url,
            'ollama_chat_model': ollama_chat_model,
            'ollama_embeddings_model': ollama_embeddings_model,
            'ollama_reachable': ollama_reachable,
        },
        'db': db_ok,
        'redis': redis_ok,
    }


app.include_router(auth.router)
app.include_router(license.router)
app.include_router(users.router)
app.include_router(tags.router)
app.include_router(departments.router)
app.include_router(folders.router)
app.include_router(documents.router)
app.include_router(ai_document_summarizer.router)
app.include_router(chat.router)
app.include_router(email_helper.router)
app.include_router(personal_notes.router)
app.include_router(dashboard.router)
app.include_router(settings_routes.router)
