from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes import folders
from app.core.rbac import require_roles
from app.models.folder import Folder
from app.models.user import Role
from app.schemas.folder import FolderCreate, FolderUpdate


class DummyQuery:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self.row

    def all(self):
        return self.rows


class DummyDB:
    def __init__(self, queue=None, rows=None):
        self.queue = list(queue or [])
        self.rows = rows or []
        self.added = []
        self.deleted = []
        self.committed = False
        self.query_args = []

    def query(self, model):
        self.query_args.append(model)
        row = self.queue.pop(0) if self.queue else None
        return DummyQuery(row=row, rows=self.rows)

    def add(self, obj):
        self.added.append(obj)

    def delete(self, obj):
        self.deleted.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        if getattr(obj, 'id', None) is None:
            obj.id = 77
        if getattr(obj, 'created_at', None) is None:
            obj.created_at = datetime.now(UTC)


def test_list_folders_returns_sorted_rows():
    rows = [SimpleNamespace(id=1, name='A'), SimpleNamespace(id=2, name='B')]
    db = DummyDB(rows=rows)

    out = folders.list_folders(db=db, _=SimpleNamespace(id=1))

    assert out == rows


def test_create_folder_success(monkeypatch):
    monkeypatch.setattr(folders, 'validate_csrf', lambda request: None)
    db = DummyDB(queue=[None])

    out = folders.create_folder(
        payload=FolderCreate(name='  Contracts  '),
        request=object(),
        db=db,
        _=SimpleNamespace(id=1, role=Role.admin),
    )

    assert db.committed is True
    assert len(db.added) == 1
    assert db.added[0].name == 'Contracts'
    assert out.id == 77


def test_create_folder_rejects_duplicate_name_case_insensitive(monkeypatch):
    monkeypatch.setattr(folders, 'validate_csrf', lambda request: None)
    db = DummyDB(queue=[SimpleNamespace(id=5)])

    with pytest.raises(HTTPException) as exc:
        folders.create_folder(
            payload=FolderCreate(name='contracts'),
            request=object(),
            db=db,
            _=SimpleNamespace(id=1, role=Role.editor),
        )

    assert exc.value.status_code == 400
    assert 'already exists' in str(exc.value.detail)


def test_update_folder_success(monkeypatch):
    monkeypatch.setattr(folders, 'validate_csrf', lambda request: None)
    row = SimpleNamespace(id=5, name='Old Name')
    db = DummyDB(queue=[row, None])

    out = folders.update_folder(
        folder_id=5,
        payload=FolderUpdate(name='  New Name '),
        request=object(),
        db=db,
        _=SimpleNamespace(id=1, role=Role.admin),
    )

    assert db.committed is True
    assert row.name == 'New Name'
    assert out == row


def test_delete_folder_success(monkeypatch):
    monkeypatch.setattr(folders, 'validate_csrf', lambda request: None)
    row = SimpleNamespace(id=8, name='Delete Me')
    db = DummyDB(queue=[row])

    out = folders.delete_folder(
        folder_id=8,
        request=object(),
        db=db,
        _=SimpleNamespace(id=1, role=Role.editor),
    )

    assert db.deleted == [row]
    assert db.committed is True
    assert out == {'message': 'Deleted'}


def test_folder_mutations_forbid_viewer():
    checker = require_roles(Role.admin, Role.editor)
    with pytest.raises(HTTPException) as exc:
        checker(current_user=SimpleNamespace(role=Role.viewer))
    assert exc.value.status_code == 403
