from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'KnowledgeBase AI'
    app_env: str = 'development'
    app_host: str = '0.0.0.0'
    app_port: int = 8000
    frontend_url: str = 'http://localhost:3000'

    database_url: str = Field(default='postgresql+psycopg://postgres:postgres@postgres:5432/knowledgebase')
    redis_url: str = Field(default='redis://redis:6379/0')

    jwt_secret: str = Field(default='change-me')
    secrets_encryption_key: str = ''
    jwt_algorithm: str = 'HS256'
    jwt_expire_hours: int = 8
    jwt_cookie_name: str = 'kb_access_token'
    csrf_cookie_name: str = 'kb_csrf_token'
    csrf_header_name: str = 'X-CSRF-Token'
    cookie_secure: bool = False

    llm_provider: str = 'openai'
    embeddings_provider: str = 'openai'
    openai_api_key: str = ''
    openai_chat_model: str = 'gpt-4.1-mini'
    openai_embeddings_model: str = 'text-embedding-3-small'
    ollama_base_url: str = 'http://host.docker.internal:11434'
    ollama_chat_model: str = 'llama3.1:8b'
    ollama_embeddings_model: str = 'nomic-embed-text'

    embedding_dimension: int = 1536
    retrieval_top_k: int = 8
    retrieval_low_conf_threshold: float = 0.35

    file_storage_path: str = '/data/uploads'
    app_log_dir: str = '/data/logs'
    app_log_level: str = 'INFO'
    app_log_max_bytes: int = 5 * 1024 * 1024
    app_log_backup_count: int = 5
    app_log_export_window_hours: int = 72
    app_log_export_max_lines: int = 10000
    max_upload_mb: int = 50
    allowed_extensions: str = 'pdf,txt,csv'
    allowed_mime_types: str = 'application/pdf,text/plain,text/csv,application/csv,application/vnd.ms-excel'

    license_server_base_url: str = 'https://app.automateki.de'
    license_server_admin_token: str = ''
    license_workspace_id: str = ''
    license_company_name: str = 'KnowledgeBase AI'
    license_billing_email: str = ''
    license_enforcement_enabled: bool = False
    license_validate_interval_hours: int = 6
    license_offline_grace_hours: int = 24
    license_request_timeout_seconds: int = 10

    celery_task_always_eager: bool = False

    chat_rate_limit_window_sec: int = 300
    chat_rate_limit_max_requests: int = 30

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def allowed_extensions_set(self) -> set[str]:
        return {x.strip().lower() for x in self.allowed_extensions.split(',') if x.strip()}

    @property
    def allowed_mime_types_set(self) -> set[str]:
        return {x.strip().lower() for x in self.allowed_mime_types.split(',') if x.strip()}

    @property
    def effective_license_admin_token(self) -> str:
        return self.license_server_admin_token.strip()

    @property
    def effective_license_validation_minutes(self) -> int:
        return max(self.license_validate_interval_hours, 1) * 60

    @property
    def effective_license_grace_hours(self) -> int:
        return max(self.license_offline_grace_hours, 1)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
