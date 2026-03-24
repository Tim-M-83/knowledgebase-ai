from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.document import Document, DocumentVisibility
from app.models.user import Role, User


def require_roles(*roles: Role) -> Callable:
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient permissions')
        return current_user

    return checker


def allowed_document_query(db: Session, user: User):
    if user.role == Role.admin:
        return db.query(Document)

    filters = [Document.visibility == DocumentVisibility.company]
    if user.department_id is not None:
        filters.append(
            (Document.visibility == DocumentVisibility.department)
            & (Document.department_id == user.department_id)
        )

    filters.append(
        (Document.visibility == DocumentVisibility.private)
        & (Document.owner_id == user.id)
    )

    return db.query(Document).filter(or_(*filters))


def ensure_can_access_document(document: Document, user: User) -> None:
    if user.role == Role.admin:
        return
    if document.visibility == DocumentVisibility.company:
        return
    if document.visibility == DocumentVisibility.department and user.department_id == document.department_id:
        return
    if document.visibility == DocumentVisibility.private and document.owner_id == user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied for document')


def ensure_can_manage_document(document: Document, user: User) -> None:
    if user.role == Role.admin:
        return
    if user.role == Role.editor and document.owner_id == user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Cannot manage this document')
