from app.schemas.chat import ChatMessageOut


def test_chat_message_schema_contains_sources_field():
    fields = set(ChatMessageOut.model_fields.keys())
    assert 'sources' in fields
