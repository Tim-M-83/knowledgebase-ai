from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.rbac import require_roles
from app.core.security import get_password_hash, validate_csrf
from app.db.session import get_db
from app.models.user import Role, User
from app.schemas.user import UserCreate, UserOut, UserUpdate


router = APIRouter(prefix='/users', tags=['users'])


@router.get('', response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin)),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post('', response_model=UserOut)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin)),
):
    validate_csrf(request)
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail='Email already exists')

    user = User(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        department_id=payload.department_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put('/{user_id}', response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin)),
):
    validate_csrf(request)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    if payload.email is not None:
        user.email = payload.email
    if payload.password is not None:
        user.password_hash = get_password_hash(payload.password)
    if payload.role is not None:
        user.role = payload.role
    if payload.department_id is not None:
        user.department_id = payload.department_id

    db.commit()
    db.refresh(user)
    return user


@router.delete('/{user_id}')
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin)),
):
    validate_csrf(request)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    db.delete(user)
    db.commit()
    return {'message': 'Deleted'}
