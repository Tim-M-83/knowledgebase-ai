from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.rbac import require_roles
from app.core.security import get_current_user, validate_csrf
from app.db.session import get_db
from app.models.department import Department
from app.models.user import Role, User
from app.schemas.department import DepartmentCreate, DepartmentOut, DepartmentUpdate


router = APIRouter(prefix='/departments', tags=['departments'])


@router.get('', response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Department).order_by(Department.name.asc()).all()


@router.post('', response_model=DepartmentOut)
def create_department(
    payload: DepartmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin, Role.editor)),
):
    validate_csrf(request)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail='Department name is required')
    exists = db.query(Department.id).filter(func.lower(Department.name) == name.lower()).first()
    if exists:
        raise HTTPException(status_code=400, detail='Department name already exists')
    dep = Department(name=name)
    db.add(dep)
    db.commit()
    db.refresh(dep)
    return dep


@router.put('/{department_id}', response_model=DepartmentOut)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin)),
):
    validate_csrf(request)
    dep = db.query(Department).filter(Department.id == department_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail='Department not found')
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail='Department name is required')
    exists = (
        db.query(Department.id)
        .filter(func.lower(Department.name) == name.lower(), Department.id != department_id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail='Department name already exists')
    dep.name = name
    db.commit()
    db.refresh(dep)
    return dep


@router.delete('/{department_id}')
def delete_department(
    department_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin)),
):
    validate_csrf(request)
    dep = db.query(Department).filter(Department.id == department_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail='Department not found')

    db.delete(dep)
    db.commit()
    return {'message': 'Deleted'}
