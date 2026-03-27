import pytest
from pydantic import ValidationError

from app.schemas.summarizer import (
    SummarizerAskRequest,
    SummarizerDocumentOut,
    SummarizerMessageOut,
    SummarizerSummarizeRequest,
)


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
        'detected_language_code',
        'created_at',
    }.issubset(document_fields)

    message_fields = set(SummarizerMessageOut.model_fields.keys())
    assert {'id', 'document_id', 'role', 'content', 'created_at'}.issubset(message_fields)

    ask_fields = set(SummarizerAskRequest.model_fields.keys())
    assert ask_fields == {
        'question',
        'response_language_mode',
        'custom_response_language',
        'browser_language',
    }


def test_summarizer_language_requests_require_custom_language():
    with pytest.raises(ValidationError):
        SummarizerSummarizeRequest(response_language_mode='custom')

    request = SummarizerAskRequest(
        question='Bitte zusammenfassen',
        response_language_mode='custom',
        custom_response_language='Deutsch',
        browser_language='de-DE',
    )
    assert request.custom_response_language == 'Deutsch'
    assert request.browser_language == 'de-DE'
