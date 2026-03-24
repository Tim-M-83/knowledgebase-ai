from abc import ABC, abstractmethod
from collections.abc import Iterator


class LLMProvider(ABC):
    @abstractmethod
    def stream_chat(self, system_prompt: str, messages: list[dict], context_chunks: list[dict]) -> Iterator[str]:
        raise NotImplementedError
