from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.rbac import require_roles
from app.core.security import get_current_user, validate_csrf
from app.db.session import get_db
from app.models.folder import Folder
from app.models.user import Role, User
from app.schemas.folder import FolderCreate, FolderOut, FolderUpdate


router = APIRouter(prefix='/folders', tags=['folders'])


@router.get('', response_model=list[FolderOut])
def list_folders(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Folder).order_by(Folder.name.asc()).all()


@router.post('', response_model=FolderOut)
def create_folder(
    payload: FolderCreate,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin, Role.editor)),
):
    validate_csrf(request)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail='Folder name is required')
    exists = db.query(Folder.id).filter(func.lower(Folder.name) == name.lower()).first()
    if exists:
        raise HTTPException(status_code=400, detail='Folder name already exists')
    folder = Folder(name=name)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


@router.put('/{folder_id}', response_model=FolderOut)
def update_folder(
    folder_id: int,
    payload: FolderUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin, Role.editor)),
):
    validate_csrf(request)
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail='Folder not found')
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail='Folder name is required')
    exists = (
        db.query(Folder.id)
        .filter(func.lower(Folder.name) == name.lower(), Folder.id != folder_id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail='Folder name already exists')
    folder.name = name
    db.commit()
    db.refresh(folder)
    return folder


@router.delete('/{folder_id}')
def delete_folder(
    folder_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin, Role.editor)),
):
    validate_csrf(request)
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail='Folder not found')
    db.delete(folder)
    db.commit()
    return {'message': 'Deleted'}
