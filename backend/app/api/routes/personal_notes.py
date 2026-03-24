from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.security import get_current_user, validate_csrf
from app.db.session import get_db
from app.models.personal_note import PersonalNote
from app.models.user import User
from app.schemas.personal_note import PersonalNoteCreate, PersonalNoteOut, PersonalNoteUpdate


router = APIRouter(prefix='/personal-notes', tags=['personal-notes'])
ALLOWED_PRIORITIES = {'none', 'low', 'medium', 'high'}


def _validate_priority(priority: str) -> str:
    clean_priority = priority.strip().lower()
    if clean_priority not in ALLOWED_PRIORITIES:
        raise HTTPException(status_code=400, detail='Priority must be one of: none, low, medium, high')
    return clean_priority


def _validate_note_payload(title: str, content: str) -> tuple[str, str]:
    clean_title = title.strip()
    clean_content = content.strip()
    if not clean_title:
        raise HTTPException(status_code=400, detail='Title is required')
    if len(clean_title) > 160:
        raise HTTPException(status_code=400, detail='Title must be 160 characters or fewer')
    if not clean_content:
        raise HTTPException(status_code=400, detail='Content is required')
    return clean_title, clean_content


@router.get('', response_model=list[PersonalNoteOut])
def list_notes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(PersonalNote)
        .filter(PersonalNote.user_id == current_user.id)
        .order_by(PersonalNote.updated_at.desc())
        .all()
    )


@router.post('', response_model=PersonalNoteOut)
def create_note(
    payload: PersonalNoteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_csrf(request)
    title, content = _validate_note_payload(payload.title, payload.content)
    priority = _validate_priority(payload.priority)

    note = PersonalNote(
        user_id=current_user.id,
        title=title,
        content=content,
        priority=priority,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.put('/{note_id}', response_model=PersonalNoteOut)
def update_note(
    note_id: int,
    payload: PersonalNoteUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_csrf(request)
    note = db.query(PersonalNote).filter(PersonalNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail='Note not found')
    if note.user_id != current_user.id:
        raise HTTPException(status_code=403, detail='Access denied')

    has_changes = False

    if payload.title is not None:
        clean_title = payload.title.strip()
        if not clean_title:
            raise HTTPException(status_code=400, detail='Title is required')
        if len(clean_title) > 160:
            raise HTTPException(status_code=400, detail='Title must be 160 characters or fewer')
        note.title = clean_title
        has_changes = True

    if payload.content is not None:
        clean_content = payload.content.strip()
        if not clean_content:
            raise HTTPException(status_code=400, detail='Content is required')
        note.content = clean_content
        has_changes = True

    if payload.priority is not None:
        note.priority = _validate_priority(payload.priority)
        has_changes = True

    if not has_changes:
        raise HTTPException(status_code=400, detail='At least one field must be provided')

    db.commit()
    db.refresh(note)
    return note


@router.delete('/{note_id}')
def delete_note(
    note_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_csrf(request)
    note = db.query(PersonalNote).filter(PersonalNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail='Note not found')
    if note.user_id != current_user.id:
        raise HTTPException(status_code=403, detail='Access denied')

    db.delete(note)
    db.commit()
    return {'message': 'Deleted'}
