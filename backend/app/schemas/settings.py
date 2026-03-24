from pydantic import BaseModel, Field


class DataSettingsOut(BaseModel):
    retention_days: int
    max_upload_mb: int
    email_helper_enabled: bool


class DataSettingsUpdate(BaseModel):
    retention_days: int = Field(ge=1, le=3650)
    max_upload_mb: int = Field(ge=1, le=1024)
    email_helper_enabled: bool


class ProviderSettingsOut(BaseModel):
    llm_provider: str
    embeddings_provider: str
    available_providers: list[str]
    openai_chat_model: str
    openai_embeddings_model: str
    openai_api_key_configured: bool
    openai_api_key_masked: str | None = None
    ollama_base_url: str
    ollama_chat_model: str
    ollama_embeddings_model: str
    warning: str | None = None


class ProviderSettingsUpdate(BaseModel):
    llm_provider: str | None = Field(default=None)
    embeddings_provider: str | None = Field(default=None)
    openai_api_key: str | None = Field(default=None, min_length=20, max_length=200)
    openai_chat_model: str | None = Field(default=None, min_length=2, max_length=120)
    ollama_base_url: str | None = Field(default=None, min_length=8, max_length=300)
    ollama_chat_model: str | None = Field(default=None, min_length=2, max_length=120)
    ollama_embeddings_model: str | None = Field(default=None, min_length=2, max_length=120)


class OpenAITestRequest(BaseModel):
    openai_api_key: str | None = None


class OpenAITestResponse(BaseModel):
    ok: bool
    chat_endpoint_ok: bool
    embeddings_endpoint_ok: bool
    detail: str
    selected_chat_model: str | None = None


class OllamaTestRequest(BaseModel):
    ollama_base_url: str | None = None
    ollama_chat_model: str | None = None
    ollama_embeddings_model: str | None = None


class OllamaTestResponse(BaseModel):
    ok: bool
    chat_endpoint_ok: bool
    embeddings_endpoint_ok: bool
    detail: str
    embedding_dimension: int | None = None
