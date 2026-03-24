from openai import OpenAI

from app.core.config import get_settings
from app.services.embeddings.base import EmbeddingsProvider


settings = get_settings()


class OpenAIEmbeddingsProvider(EmbeddingsProvider):
    def __init__(self, api_key: str, model: str | None = None) -> None:
        if not api_key:
            raise ValueError('OpenAI API key is not configured')
        self.client = OpenAI(api_key=api_key, timeout=60.0, max_retries=2)
        self.model = model or settings.openai_embeddings_model

    def embed_text(self, text: str) -> list[float]:
        response = self.client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]
