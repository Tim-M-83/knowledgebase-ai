from collections.abc import Iterator

from openai import OpenAI

from app.core.config import get_settings
from app.services.llm.base import LLMProvider


settings = get_settings()


class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str | None = None) -> None:
        if not api_key:
            raise ValueError('OpenAI API key is not configured')
        self.client = OpenAI(api_key=api_key, timeout=60.0, max_retries=2)
        self.model = model or settings.openai_chat_model

    def stream_chat(self, system_prompt: str, messages: list[dict], context_chunks: list[dict]) -> Iterator[str]:
        context_text = '\n\n'.join([f"[{i + 1}] {chunk['content']}" for i, chunk in enumerate(context_chunks)])

        input_messages: list[dict] = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'system', 'content': f'Context chunks (cite as [n]):\\n{context_text}'},
        ]

        for message in messages:
            role = message.get('role', 'user')
            if role not in {'user', 'assistant', 'system'}:
                role = 'user'
            input_messages.append({'role': role, 'content': message.get('content', '')})

        try:
            with self.client.responses.stream(
                model=self.model,
                input=input_messages,
                temperature=0.1,
            ) as stream:
                for event in stream:
                    if event.type == 'response.output_text.delta':
                        yield event.delta
            return
        except Exception:
            pass

        # Fallback for projects/models that are available via Chat Completions but not Responses.
        with self.client.chat.completions.stream(
            model=self.model,
            messages=input_messages,
            temperature=0.1,
        ) as stream:
            for event in stream:
                if event.type == 'content.delta' and event.delta:
                    yield event.delta
