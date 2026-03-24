from app.schemas.summarizer import SummarizerAskRequest, SummarizerDocumentOut, SummarizerMessageOut


def test_summarizer_schema_fields():
    document_fields = set(SummarizerDocumentOut.model_fields.keys())
    assert {
        'id',
        'owner_id',
        'original_name',
        'mime_type',
        'size',
        'status',
        'error_text',
        'summary_text',
        'summary_updated_at',
        'created_at',
    }.issubset(document_fields)

    message_fields = set(SummarizerMessageOut.model_fields.keys())
    assert {'id', 'document_id', 'role', 'content', 'created_at'}.issubset(message_fields)

    ask_fields = set(SummarizerAskRequest.model_fields.keys())
    assert ask_fields == {'question'}
