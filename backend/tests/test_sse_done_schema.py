from app.schemas.chat import SSEDoneEvent


def test_sse_done_schema_contains_required_fields():
    fields = set(SSEDoneEvent.model_fields.keys())
    assert {'answer', 'session_id', 'message_id', 'low_confidence', 'warning'}.issubset(fields)
