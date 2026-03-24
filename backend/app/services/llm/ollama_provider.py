import json
from collections.abc import Iterator

import httpx

from app.services.llm.base import LLMProvider


class OllamaLLMProvider(LLMProvider):
    def __init__(self, base_url: str, model: str) -> None:
        if not base_url:
            raise ValueError('Ollama base URL is not configured')
        if not model:
            raise ValueError('Ollama chat model is not configured')
        self.base_url = base_url.rstrip('/')
        self.model = model

    def stream_chat(self, system_prompt: str, messages: list[dict], context_chunks: list[dict]) -> Iterator[str]:
        context_text = '\n\n'.join([f"[{i + 1}] {chunk['content']}" for i, chunk in enumerate(context_chunks)])
        ollama_messages: list[dict[str, str]] = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'system', 'content': f'Context chunks (cite as [n]):\n{context_text}'},
        ]

        for message in messages:
            role = message.get('role', 'user')
            if role not in {'user', 'assistant', 'system'}:
                role = 'user'
            ollama_messages.append({'role': role, 'content': str(message.get('content', ''))})

        payload = {
            'model': self.model,
            'messages': ollama_messages,
            'stream': True,
        }

        with httpx.Client(timeout=60.0) as client:
            with client.stream('POST', f'{self.base_url}/api/chat', json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    event = json.loads(line)
                    if event.get('error'):
                        raise ValueError(f"Ollama chat failed: {event['error']}")
                    chunk = (event.get('message') or {}).get('content', '')
                    if chunk:
                        yield chunk
