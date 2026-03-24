from sqlalchemy.orm import Session

from app.services.llm.base import LLMProvider
from app.services.llm.local_provider import LocalStubLLMProvider
from app.services.llm.ollama_provider import OllamaLLMProvider
from app.services.llm.openai_provider import OpenAILLMProvider
from app.services.provider_settings import (
    PROVIDER_OLLAMA,
    PROVIDER_OPENAI,
    get_runtime_ollama_base_url,
    get_runtime_ollama_chat_model,
    get_runtime_openai_api_key,
    get_runtime_openai_chat_model,
    get_runtime_provider_pair,
)


def get_llm_provider(db: Session | None = None) -> LLMProvider:
    llm_provider, _ = get_runtime_provider_pair(db)
    if llm_provider == PROVIDER_OPENAI:
        api_key = get_runtime_openai_api_key(db)
        model = get_runtime_openai_chat_model(db)
        return OpenAILLMProvider(api_key=api_key, model=model)
    if llm_provider == PROVIDER_OLLAMA:
        base_url = get_runtime_ollama_base_url(db)
        model = get_runtime_ollama_chat_model(db)
        return OllamaLLMProvider(base_url=base_url, model=model)
    return LocalStubLLMProvider()
