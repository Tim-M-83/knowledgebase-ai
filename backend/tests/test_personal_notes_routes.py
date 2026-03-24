from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes import personal_notes
from app.models.personal_note import PersonalNote
from app.schemas.personal_note import PersonalNoteCreate, PersonalNoteUpdate


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
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []
        self.query_model = None
        self.committed = False
        self.added = []
        self.deleted = []

    def query(self, model):
        self.query_model = model
        if model is PersonalNote:
            return DummyQuery(self.row, self.rows)
        raise AssertionError(f'Unexpected model {model}')

    def add(self, obj):
        self.added.append(obj)

    def delete(self, obj):
        self.deleted.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        if getattr(obj, 'id', None) is None:
            obj.id = 99
        if getattr(obj, 'created_at', None) is None:
            obj.created_at = datetime.now(UTC)
        obj.updated_at = datetime.now(UTC)


def test_list_notes_returns_current_user_rows():
    now = datetime.now(UTC)
    rows = [
        SimpleNamespace(
            id=1,
            user_id=5,
            title='A',
            content='First',
            priority='none',
            created_at=now,
            updated_at=now,
        ),
        SimpleNamespace(
            id=2,
            user_id=5,
            title='B',
            content='Second',
            priority='low',
            created_at=now,
            updated_at=now,
        ),
    ]
    db = DummyDB(rows=rows)

    out = personal_notes.list_notes(db=db, current_user=SimpleNamespace(id=5))

    assert db.query_model is PersonalNote
    assert out == rows


def test_create_note_trims_payload_and_persists(monkeypatch):
    monkeypatch.setattr(personal_notes, 'validate_csrf', lambda request: None)
    db = DummyDB()
    current_user = SimpleNamespace(id=5)

    out = personal_notes.create_note(
        payload=PersonalNoteCreate(title='  My Note  ', content='  Keep this private  '),
        request=object(),
        db=db,
        current_user=current_user,
    )

    assert db.query_model is None
    assert db.committed is True
    assert len(db.added) == 1
    assert db.added[0].user_id == 5
    assert db.added[0].title == 'My Note'
    assert db.added[0].content == 'Keep this private'
    assert db.added[0].priority == 'none'
    assert out.id == 99


def test_create_note_accepts_priority(monkeypatch):
    monkeypatch.setattr(personal_notes, 'validate_csrf', lambda request: None)
    db = DummyDB()
    current_user = SimpleNamespace(id=5)

    personal_notes.create_note(
        payload=PersonalNoteCreate(title='Priority Note', content='Body', priority='high'),
        request=object(),
        db=db,
        current_user=current_user,
    )

    assert db.added[0].priority == 'high'


@pytest.mark.parametrize(
    'payload, expected_detail',
    [
        (PersonalNoteCreate(title='   ', content='Body'), 'Title is required'),
        (PersonalNoteCreate(title='Title', content='   '), 'Content is required'),
        (SimpleNamespace(title='Title', content='Body', priority='nonee'), 'Priority must be one of'),
    ],
)
def test_create_note_validates_required_fields(monkeypatch, payload, expected_detail):
    monkeypatch.setattr(personal_notes, 'validate_csrf', lambda request: None)
    db = DummyDB()
    current_user = SimpleNamespace(id=5)

    with pytest.raises(HTTPException) as exc:
        personal_notes.create_note(
            payload=payload,
            request=object(),
            db=db,
            current_user=current_user,
        )

    assert exc.value.status_code == 400
    assert expected_detail in str(exc.value.detail)


def test_update_note_rejects_non_owner(monkeypatch):
    monkeypatch.setattr(personal_notes, 'validate_csrf', lambda request: None)
    note = SimpleNamespace(
        id=12,
        user_id=99,
        title='Old',
        content='Old content',
        priority='none',
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db = DummyDB(row=note)

    with pytest.raises(HTTPException) as exc:
        personal_notes.update_note(
            note_id=12,
            payload=PersonalNoteUpdate(title='New', content='New content'),
            request=object(),
            db=db,
            current_user=SimpleNamespace(id=5),
        )

    assert exc.value.status_code == 403
    assert 'Access denied' in str(exc.value.detail)


def test_update_note_owner_can_edit_with_trim(monkeypatch):
    monkeypatch.setattr(personal_notes, 'validate_csrf', lambda request: None)
    note = SimpleNamespace(
        id=7,
        user_id=5,
        title='Old',
        content='Old content',
        priority='low',
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db = DummyDB(row=note)

    out = personal_notes.update_note(
        note_id=7,
        payload=PersonalNoteUpdate(title='  New Title  ', content='  Updated text  ', priority='high'),
        request=object(),
        db=db,
        current_user=SimpleNamespace(id=5),
    )

    assert db.query_model is PersonalNote
    assert db.committed is True
    assert note.title == 'New Title'
    assert note.content == 'Updated text'
    assert note.priority == 'high'
    assert out.id == 7


def test_update_note_rejects_invalid_priority(monkeypatch):
    monkeypatch.setattr(personal_notes, 'validate_csrf', lambda request: None)
    note = SimpleNamespace(
        id=9,
        user_id=5,
        title='Old',
        content='Old content',
        priority='none',
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db = DummyDB(row=note)

    with pytest.raises(HTTPException) as exc:
        personal_notes.update_note(
            note_id=9,
            payload=SimpleNamespace(title=None, content=None, priority='invalid'),
            request=object(),
            db=db,
            current_user=SimpleNamespace(id=5),
        )

    assert exc.value.status_code == 400
    assert 'Priority must be one of' in str(exc.value.detail)


def test_update_note_requires_change_payload(monkeypatch):
    monkeypatch.setattr(personal_notes, 'validate_csrf', lambda request: None)
    note = SimpleNamespace(
        id=11,
        user_id=5,
        title='Old',
        content='Old content',
        priority='none',
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db = DummyDB(row=note)

    with pytest.raises(HTTPException) as exc:
        personal_notes.update_note(
            note_id=11,
            payload=PersonalNoteUpdate(),
            request=object(),
            db=db,
            current_user=SimpleNamespace(id=5),
        )

    assert exc.value.status_code == 400
    assert 'At least one field must be provided' in str(exc.value.detail)


def test_delete_note_rejects_non_owner(monkeypatch):
    monkeypatch.setattr(personal_notes, 'validate_csrf', lambda request: None)
    note = SimpleNamespace(
        id=33,
        user_id=2,
        title='X',
        content='Y',
        priority='none',
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db = DummyDB(row=note)

    with pytest.raises(HTTPException) as exc:
        personal_notes.delete_note(
            note_id=33,
            request=object(),
            db=db,
            current_user=SimpleNamespace(id=5),
        )

    assert exc.value.status_code == 403


def test_delete_note_owner_can_delete(monkeypatch):
    monkeypatch.setattr(personal_notes, 'validate_csrf', lambda request: None)
    note = SimpleNamespace(
        id=44,
        user_id=5,
        title='X',
        content='Y',
        priority='none',
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db = DummyDB(row=note)

    out = personal_notes.delete_note(
        note_id=44,
        request=object(),
        db=db,
        current_user=SimpleNamespace(id=5),
    )

    assert db.committed is True
    assert db.deleted == [note]
    assert out == {'message': 'Deleted'}
