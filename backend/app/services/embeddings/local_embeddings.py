import hashlib
import random

from app.core.config import get_settings
from app.services.embeddings.base import EmbeddingsProvider


settings = get_settings()


class LocalStubEmbeddingsProvider(EmbeddingsProvider):
    def _vector_for_text(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
        seed = int(digest[:16], 16)
        rng = random.Random(seed)
        return [rng.uniform(-1.0, 1.0) for _ in range(settings.embedding_dimension)]

    def embed_text(self, text: str) -> list[float]:
        return self._vector_for_text(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._vector_for_text(text) for text in texts]
