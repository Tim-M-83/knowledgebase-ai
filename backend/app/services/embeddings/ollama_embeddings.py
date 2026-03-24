import httpx

from app.core.config import get_settings
from app.services.embeddings.base import EmbeddingsProvider


settings = get_settings()


class OllamaEmbeddingsProvider(EmbeddingsProvider):
    def __init__(self, base_url: str, model: str) -> None:
        if not base_url:
            raise ValueError('Ollama base URL is not configured')
        if not model:
            raise ValueError('Ollama embeddings model is not configured')
        self.base_url = base_url.rstrip('/')
        self.model = model

    def _normalize_dim(self, vector: list[float]) -> list[float]:
        target = settings.embedding_dimension
        if len(vector) == target:
            return vector
        if len(vector) > target:
            return vector[:target]
        return vector + [0.0] * (target - len(vector))

    def _extract_embeddings(self, payload: dict) -> list[list[float]]:
        embeddings = payload.get('embeddings')
        if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], list):
            return [self._normalize_dim([float(v) for v in item]) for item in embeddings]
        if isinstance(embeddings, list) and (not embeddings or isinstance(embeddings[0], (float, int))):
            return [self._normalize_dim([float(v) for v in embeddings])]
        return []

    def _embed_with_api_embed(self, texts: list[str]) -> list[list[float]]:
        body = {'model': self.model, 'input': texts if len(texts) > 1 else texts[0]}
        with httpx.Client(timeout=60.0) as client:
            response = client.post(f'{self.base_url}/api/embed', json=body)
            response.raise_for_status()
            parsed = response.json()
            vectors = self._extract_embeddings(parsed)
            if not vectors:
                raise ValueError('Ollama /api/embed returned no embeddings')
            return vectors

    def _embed_with_api_embeddings(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        with httpx.Client(timeout=60.0) as client:
            for text in texts:
                response = client.post(
                    f'{self.base_url}/api/embeddings',
                    json={'model': self.model, 'prompt': text},
                )
                response.raise_for_status()
                parsed = response.json()
                vector = parsed.get('embedding')
                if not isinstance(vector, list):
                    raise ValueError('Ollama /api/embeddings returned invalid embedding payload')
                vectors.append(self._normalize_dim([float(v) for v in vector]))
        return vectors

    def embed_text(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            return self._embed_with_api_embed(texts)
        except Exception:
            return self._embed_with_api_embeddings(texts)
