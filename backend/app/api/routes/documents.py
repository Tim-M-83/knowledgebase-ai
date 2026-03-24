import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rbac import (
    allowed_document_query,
    ensure_can_access_document,
    ensure_can_manage_document,
    require_roles,
)
from app.core.security import get_current_user, validate_csrf
from app.db.session import get_db
from app.models.chunk import Chunk
from app.models.department import Department
from app.models.document import Document, DocumentStatus, DocumentTag, DocumentVisibility
from app.models.folder import Folder
from app.models.tag import Tag
from app.models.user import Role, User
from app.schemas.document import DocumentDetail, DocumentMetadataUpdate, DocumentOut
from app.tasks.ingestion_tasks import ingest_document_task
from app.utils.file_storage import delete_file, load_file_path, store_upload_file


router = APIRouter(prefix='/documents', tags=['documents'])
settings = get_settings()
logger = logging.getLogger(__name__)


def _build_document_detail(db: Session, document: Document) -> DocumentDetail:
    chunk_count = db.query(Chunk).filter(Chunk.document_id == document.id).count()
    tag_ids = [row.tag_id for row in db.query(DocumentTag).filter(DocumentTag.document_id == document.id).all()]
    return DocumentDetail(
        id=document.id,
        owner_id=document.owner_id,
        filename=document.filename,
        original_name=document.original_name,
        mime_type=document.mime_type,
        size=document.size,
        department_id=document.department_id,
        folder_id=document.folder_id,
        visibility=document.visibility,
        status=document.status,
        error_text=document.error_text,
        created_at=document.created_at,
        chunk_count=chunk_count,
        tag_ids=tag_ids,
    )


def _enqueue_document_index(db: Session, document: Document) -> Document:
    document.status = DocumentStatus.uploaded
    document.error_text = None
    db.commit()
    ingest_document_task.delay(document.id)
    db.refresh(document)
    return document


@router.post('/upload', response_model=DocumentOut)
def upload_document(
    request: Request,
    file: UploadFile = File(...),
    department_id: int | None = Form(default=None),
    folder_id: int | None = Form(default=None),
    visibility: DocumentVisibility = Form(default=DocumentVisibility.company),
    tag_ids: str = Form(default=''),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin, Role.editor)),
):
    validate_csrf(request)

    if not file.filename or '.' not in file.filename:
        raise HTTPException(status_code=400, detail='File must include an extension')

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in settings.allowed_extensions_set:
        raise HTTPException(status_code=400, detail='Unsupported file type')

    if (file.content_type or '').lower() not in settings.allowed_mime_types_set:
        raise HTTPException(status_code=400, detail='Unsupported MIME type')

    if department_id is not None:
        department = db.query(Department).filter(Department.id == department_id).first()
        if not department:
            raise HTTPException(status_code=400, detail='Invalid department_id')
    if folder_id is not None:
        folder = db.query(Folder).filter(Folder.id == folder_id).first()
        if not folder:
            raise HTTPException(status_code=400, detail='Invalid folder_id')

    parsed_tag_ids: list[int] = []
    if tag_ids.strip():
        parsed_tag_ids = list(dict.fromkeys([int(x) for x in tag_ids.split(',') if x.strip().isdigit()]))
        if parsed_tag_ids:
            existing_tag_ids = {row[0] for row in db.query(Tag.id).filter(Tag.id.in_(parsed_tag_ids)).all()}
            missing = [tag_id for tag_id in parsed_tag_ids if tag_id not in existing_tag_ids]
            if missing:
                raise HTTPException(status_code=400, detail=f'Invalid tag_ids: {missing}')

    stored_name, size = store_upload_file(file)
    if size > settings.max_upload_bytes:
        delete_file(stored_name)
        raise HTTPException(status_code=400, detail=f'File too large. Max {settings.max_upload_mb}MB')

    document = Document(
        owner_id=current_user.id,
        filename=stored_name,
        original_name=file.filename,
        mime_type=file.content_type or 'application/octet-stream',
        size=size,
        department_id=department_id,
        folder_id=folder_id,
        visibility=visibility,
        status=DocumentStatus.uploaded,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    if parsed_tag_ids:
        for tag_id in parsed_tag_ids:
            db.add(DocumentTag(document_id=document.id, tag_id=tag_id))
        db.commit()

    ingest_document_task.delay(document.id)
    logger.info(
        'Document uploaded document_id=%s owner_id=%s visibility=%s status=%s',
        document.id,
        current_user.id,
        document.visibility.value,
        document.status.value,
    )
    return document


@router.get('', response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = allowed_document_query(db, current_user)
    return query.order_by(Document.created_at.desc()).all()


@router.get('/{document_id}', response_model=DocumentDetail)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail='Document not found')
    ensure_can_access_document(document, current_user)
    return _build_document_detail(db, document)


@router.get('/{document_id}/file')
def view_document_file(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail='Document not found')
    ensure_can_access_document(document, current_user)

    try:
        path = load_file_path(document.filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='Stored file not found') from None

    return FileResponse(
        path=path,
        media_type=document.mime_type or 'application/octet-stream',
        filename=document.original_name,
        content_disposition_type='inline',
    )


@router.put('/{document_id}/metadata', response_model=DocumentDetail)
def update_document_metadata(
    document_id: int,
    payload: DocumentMetadataUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin, Role.editor)),
):
    validate_csrf(request)
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail='Document not found')
    ensure_can_manage_document(document, current_user)

    if 'department_id' in payload.model_fields_set:
        if payload.department_id is not None:
            department = db.query(Department).filter(Department.id == payload.department_id).first()
            if not department:
                raise HTTPException(status_code=400, detail='Invalid department_id')
        document.department_id = payload.department_id

    if 'folder_id' in payload.model_fields_set:
        if payload.folder_id is not None:
            folder = db.query(Folder).filter(Folder.id == payload.folder_id).first()
            if not folder:
                raise HTTPException(status_code=400, detail='Invalid folder_id')
        document.folder_id = payload.folder_id

    if 'tag_ids' in payload.model_fields_set:
        normalized_tag_ids = list(dict.fromkeys(payload.tag_ids or []))
        if normalized_tag_ids:
            existing_tag_ids = {
                row[0] for row in db.query(Tag.id).filter(Tag.id.in_(normalized_tag_ids)).all()
            }
            missing = [tag_id for tag_id in normalized_tag_ids if tag_id not in existing_tag_ids]
            if missing:
                raise HTTPException(status_code=400, detail=f'Invalid tag_ids: {missing}')

        db.query(DocumentTag).filter(DocumentTag.document_id == document.id).delete()
        for tag_id in normalized_tag_ids:
            db.add(DocumentTag(document_id=document.id, tag_id=tag_id))

    db.commit()
    db.refresh(document)
    logger.info('Document metadata updated document_id=%s user_id=%s', document.id, current_user.id)
    return _build_document_detail(db, document)


@router.delete('/{document_id}')
def delete_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin, Role.editor)),
):
    validate_csrf(request)
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail='Document not found')
    ensure_can_manage_document(document, current_user)

    filename = document.filename
    db.delete(document)
    db.commit()
    delete_file(filename)
    logger.info('Document deleted document_id=%s user_id=%s', document_id, current_user.id)
    return {'message': 'Deleted'}


@router.post('/{document_id}/index', response_model=DocumentOut)
def index_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin, Role.editor)),
):
    validate_csrf(request)
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Document not found')
    ensure_can_manage_document(document, current_user)
    logger.info('Document reindex requested document_id=%s user_id=%s', document.id, current_user.id)
    return _enqueue_document_index(db, document)


@router.post('/{document_id}/reingest', response_model=DocumentOut)
def reingest_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin, Role.editor)),
):
    return index_document(document_id=document_id, request=request, db=db, current_user=current_user)
