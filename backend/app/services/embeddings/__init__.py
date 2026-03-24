from sqlalchemy.orm import Session

from app.services.embeddings.base import EmbeddingsProvider
from app.services.embeddings.local_embeddings import LocalStubEmbeddingsProvider
from app.services.embeddings.ollama_embeddings import OllamaEmbeddingsProvider
from app.services.embeddings.openai_embeddings import OpenAIEmbeddingsProvider
from app.services.provider_settings import (
    PROVIDER_OLLAMA,
    PROVIDER_OPENAI,
    get_runtime_ollama_base_url,
    get_runtime_ollama_embeddings_model,
    get_runtime_openai_api_key,
    get_runtime_provider_pair,
)


def get_embeddings_provider(db: Session | None = None) -> EmbeddingsProvider:
    _, embeddings_provider = get_runtime_provider_pair(db)
    if embeddings_provider == PROVIDER_OPENAI:
        api_key = get_runtime_openai_api_key(db)
        return OpenAIEmbeddingsProvider(api_key=api_key, model=None)
    if embeddings_provider == PROVIDER_OLLAMA:
        base_url = get_runtime_ollama_base_url(db)
        model = get_runtime_ollama_embeddings_model(db)
        return OllamaEmbeddingsProvider(base_url=base_url, model=model)
    return LocalStubEmbeddingsProvider()
