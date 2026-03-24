from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes import ai_document_summarizer


def test_validate_upload_file_accepts_docx():
    file = SimpleNamespace(
        filename='external-report.docx',
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )
    ai_document_summarizer._validate_upload_file(file)


def test_validate_upload_file_rejects_legacy_doc():
    file = SimpleNamespace(
        filename='legacy-contract.doc',
        content_type='application/msword',
    )
    with pytest.raises(HTTPException) as exc:
        ai_document_summarizer._validate_upload_file(file)
    assert exc.value.status_code == 400
    assert 'Please upload DOCX' in str(exc.value.detail)


def test_validate_upload_file_rejects_unknown_extension():
    file = SimpleNamespace(filename='archive.zip', content_type='application/zip')
    with pytest.raises(HTTPException) as exc:
        ai_document_summarizer._validate_upload_file(file)
    assert exc.value.status_code == 400
    assert 'Unsupported file type' in str(exc.value.detail)


class DummyQuery:
    def __init__(self, row):
        self.row = row

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.row


class DummyDB:
    def __init__(self, row):
        self.row = row

    def query(self, model):
        return DummyQuery(self.row)


def test_get_owned_document_requires_owner():
    db = DummyDB(SimpleNamespace(id=7, owner_id=99))
    with pytest.raises(HTTPException) as exc:
        ai_document_summarizer._get_owned_document(
            db=db,
            document_id=7,
            current_user=SimpleNamespace(id=5),
        )
    assert exc.value.status_code == 403


def test_get_owned_document_not_found():
    db = DummyDB(None)
    with pytest.raises(HTTPException) as exc:
        ai_document_summarizer._get_owned_document(
            db=db,
            document_id=7,
            current_user=SimpleNamespace(id=5),
        )
    assert exc.value.status_code == 404
