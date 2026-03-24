from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.rbac import require_roles
from app.core.security import get_current_user, validate_csrf
from app.db.session import get_db
from app.models.tag import Tag
from app.models.user import Role, User
from app.schemas.tag import TagCreate, TagOut, TagUpdate


router = APIRouter(prefix='/tags', tags=['tags'])


@router.get('', response_model=list[TagOut])
def list_tags(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Tag).order_by(Tag.name.asc()).all()


@router.post('', response_model=TagOut)
def create_tag(
    payload: TagCreate,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin, Role.editor)),
):
    validate_csrf(request)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail='Tag name is required')
    exists = db.query(Tag.id).filter(func.lower(Tag.name) == name.lower()).first()
    if exists:
        raise HTTPException(status_code=400, detail='Tag name already exists')
    tag = Tag(name=name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.put('/{tag_id}', response_model=TagOut)
def update_tag(
    tag_id: int,
    payload: TagUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin)),
):
    validate_csrf(request)
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail='Tag not found')
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail='Tag name is required')
    exists = (
        db.query(Tag.id)
        .filter(func.lower(Tag.name) == name.lower(), Tag.id != tag_id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail='Tag name already exists')
    tag.name = name
    db.commit()
    db.refresh(tag)
    return tag


@router.delete('/{tag_id}')
def delete_tag(
    tag_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin)),
):
    validate_csrf(request)
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail='Tag not found')
    db.delete(tag)
    db.commit()
    return {'message': 'Deleted'}
