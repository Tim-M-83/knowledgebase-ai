from app.api.routes.chat import build_system_prompt


def test_prompt_includes_required_markdown_sections():
    prompt = build_system_prompt()
    assert '## Direct Answer' in prompt
    assert '## Key Points' in prompt
    assert '## Evidence' in prompt
    assert '## Limitations' in prompt


def test_prompt_mentions_citation_contract():
    prompt = build_system_prompt()
    assert 'numeric references like [1], [2]' in prompt
