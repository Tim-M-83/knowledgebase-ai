from app.services.embeddings import get_embeddings_provider
from app.services.embeddings.ollama_embeddings import OllamaEmbeddingsProvider
from app.services.embeddings.openai_embeddings import OpenAIEmbeddingsProvider
from app.services.llm import get_llm_provider
from app.services.llm.ollama_provider import OllamaLLMProvider
from app.services.llm.openai_provider import OpenAILLMProvider
from app.services import embeddings as embeddings_module
from app.services import llm as llm_module


def test_llm_factory_uses_runtime_openai(monkeypatch):
    monkeypatch.setattr(llm_module, 'get_runtime_provider_pair', lambda db: ('openai', 'openai'))
    monkeypatch.setattr(llm_module, 'get_runtime_openai_api_key', lambda db: 'sk-test-key')
    monkeypatch.setattr(llm_module, 'get_runtime_openai_chat_model', lambda db: 'gpt-4.1-mini')

    provider = get_llm_provider(db=None)
    assert isinstance(provider, OpenAILLMProvider)


def test_llm_factory_uses_runtime_ollama(monkeypatch):
    monkeypatch.setattr(llm_module, 'get_runtime_provider_pair', lambda db: ('ollama', 'ollama'))
    monkeypatch.setattr(llm_module, 'get_runtime_ollama_base_url', lambda db: 'http://localhost:11434')
    monkeypatch.setattr(llm_module, 'get_runtime_ollama_chat_model', lambda db: 'llama3.1:8b')

    provider = get_llm_provider(db=None)
    assert isinstance(provider, OllamaLLMProvider)


def test_embeddings_factory_uses_runtime_openai(monkeypatch):
    monkeypatch.setattr(embeddings_module, 'get_runtime_provider_pair', lambda db: ('openai', 'openai'))
    monkeypatch.setattr(embeddings_module, 'get_runtime_openai_api_key', lambda db: 'sk-test-key')

    provider = get_embeddings_provider(db=None)
    assert isinstance(provider, OpenAIEmbeddingsProvider)


def test_embeddings_factory_uses_runtime_ollama(monkeypatch):
    monkeypatch.setattr(embeddings_module, 'get_runtime_provider_pair', lambda db: ('ollama', 'ollama'))
    monkeypatch.setattr(embeddings_module, 'get_runtime_ollama_base_url', lambda db: 'http://localhost:11434')
    monkeypatch.setattr(embeddings_module, 'get_runtime_ollama_embeddings_model', lambda db: 'nomic-embed-text')

    provider = get_embeddings_provider(db=None)
    assert isinstance(provider, OllamaEmbeddingsProvider)
