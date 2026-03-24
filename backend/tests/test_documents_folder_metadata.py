from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse

from app.api.routes import documents
from app.models.document import Document
from app.models.folder import Folder
from app.schemas.document import DocumentMetadataUpdate


class DummyQuery:
    def __init__(self, row=None):
        self.row = row

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return []

    def first(self):
        return self.row


class DummyDB:
    def __init__(self, document_row=None, folder_row=None):
        self.document_row = document_row
        self.folder_row = folder_row
        self.committed = False
        self.refreshed = []

    def query(self, model):
        if model is Document:
            return DummyQuery(self.document_row)
        if model is Folder:
            return DummyQuery(self.folder_row)
        return DummyQuery()

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed.append(obj)


def test_upload_document_rejects_invalid_folder_id(monkeypatch):
    monkeypatch.setattr(documents, 'validate_csrf', lambda request: None)
    db = DummyDB(folder_row=None)

    with pytest.raises(HTTPException) as exc:
        documents.upload_document(
            request=object(),
            file=SimpleNamespace(filename='test.pdf', content_type='application/pdf'),
            department_id=None,
            folder_id=123,
            db=db,
            current_user=SimpleNamespace(id=7),
        )

    assert exc.value.status_code == 400
    assert 'Invalid folder_id' in str(exc.value.detail)


def test_update_document_metadata_rejects_invalid_folder(monkeypatch):
    monkeypatch.setattr(documents, 'validate_csrf', lambda request: None)
    monkeypatch.setattr(documents, 'ensure_can_manage_document', lambda document, current_user: None)
    row = SimpleNamespace(id=10, owner_id=7, folder_id=None, department_id=None)
    db = DummyDB(document_row=row, folder_row=None)

    with pytest.raises(HTTPException) as exc:
        documents.update_document_metadata(
            document_id=10,
            payload=DocumentMetadataUpdate(folder_id=999),
            request=object(),
            db=db,
            current_user=SimpleNamespace(id=7),
        )

    assert exc.value.status_code == 400
    assert 'Invalid folder_id' in str(exc.value.detail)


def test_update_document_metadata_can_clear_folder(monkeypatch):
    monkeypatch.setattr(documents, 'validate_csrf', lambda request: None)
    monkeypatch.setattr(documents, 'ensure_can_manage_document', lambda document, current_user: None)
    monkeypatch.setattr(documents, '_build_document_detail', lambda db, document: document)
    row = SimpleNamespace(id=11, owner_id=7, folder_id=5, department_id=None)
    db = DummyDB(document_row=row, folder_row=None)

    out = documents.update_document_metadata(
        document_id=11,
        payload=DocumentMetadataUpdate(folder_id=None),
        request=object(),
        db=db,
        current_user=SimpleNamespace(id=7),
    )

    assert row.folder_id is None
    assert db.committed is True
    assert out == row


def test_view_document_file_returns_inline_file_response(monkeypatch, tmp_path):
    row = SimpleNamespace(
        id=12,
        owner_id=7,
        filename='stored.pdf',
        original_name='Original File.pdf',
        mime_type='application/pdf',
    )
    db = DummyDB(document_row=row)
    file_path = tmp_path / 'stored.pdf'
    file_path.write_text('preview')

    monkeypatch.setattr(documents, 'ensure_can_access_document', lambda document, current_user: None)
    monkeypatch.setattr(documents, 'load_file_path', lambda filename: file_path)

    response = documents.view_document_file(
        document_id=12,
        db=db,
        current_user=SimpleNamespace(id=7),
    )

    assert isinstance(response, FileResponse)
    assert response.media_type == 'application/pdf'
    assert 'inline;' in response.headers['content-disposition']
    assert 'Original%20File.pdf' in response.headers['content-disposition']


def test_view_document_file_returns_404_when_storage_file_is_missing(monkeypatch):
    row = SimpleNamespace(
        id=13,
        owner_id=7,
        filename='missing.pdf',
        original_name='Missing File.pdf',
        mime_type='application/pdf',
    )
    db = DummyDB(document_row=row)

    monkeypatch.setattr(documents, 'ensure_can_access_document', lambda document, current_user: None)
    monkeypatch.setattr(documents, 'load_file_path', lambda filename: (_ for _ in ()).throw(FileNotFoundError()))

    with pytest.raises(HTTPException) as exc:
        documents.view_document_file(
            document_id=13,
            db=db,
            current_user=SimpleNamespace(id=7),
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == 'Stored file not found'
