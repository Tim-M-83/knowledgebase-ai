import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_current_user, validate_csrf
from app.db.session import get_db
from app.models.chat import ChatRole
from app.models.summarizer import (
    SummarizerChunk,
    SummarizerDocument,
    SummarizerDocumentStatus,
    SummarizerMessage,
)
from app.models.user import User
from app.schemas.summarizer import (
    SummarizerAskRequest,
    SummarizerDocumentDetail,
    SummarizerDocumentOut,
    SummarizerMessageOut,
)
from app.services.llm import get_llm_provider
from app.services.retrieval import retrieval_confidence
from app.services.summarizer_retrieval import search_summarizer_chunks
from app.tasks.ingestion_tasks import ingest_summarizer_document_task
from app.utils.file_storage import delete_file, store_upload_file
from app.utils.rate_limit import enforce_chat_rate_limit


router = APIRouter(prefix='/ai-document-summarizer', tags=['ai-document-summarizer'])
settings = get_settings()

ALLOWED_EXTENSIONS = {'pdf', 'txt', 'csv', 'docx'}
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'text/plain',
    'text/csv',
    'application/csv',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/octet-stream',
}
LOW_CONFIDENCE_WARNING = (
    'Answer generated with low retrieval confidence. Verify against the document context.'
)


def _build_summary_prompt() -> str:
    return (
        'You are an AI document summarizer for external documents. '
        'Use only the provided context from this single document.\n\n'
        'Return Markdown with this exact structure:\n'
        '## Executive Summary\n'
        '## Most Important Information\n'
        '## Key Facts and Figures\n'
        '## Risks or Open Questions (only when needed)\n\n'
        'If context is insufficient, say that clearly.'
    )


def _build_document_chat_prompt() -> str:
    return (
        'You answer questions about one uploaded external document only. '
        'Use only the provided context chunks and do not use company knowledge.\n\n'
        'Response rules:\n'
        '- Be concise and practical.\n'
        '- Cite evidence inline with [n] references.\n'
        '- If the answer is not in the document context, say that clearly.'
    )


def _event(event_name: str, data: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(data)}\n\n"


def _source_ref(chunk: dict) -> dict:
    return {
        'id': chunk['id'],
        'chunk_id': chunk['chunk_id'],
        'score': chunk['score'],
        'snippet': chunk['snippet'],
    }


def _validate_upload_file(file: UploadFile) -> None:
    if not file.filename or '.' not in file.filename:
        raise HTTPException(status_code=400, detail='File must include an extension')

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext == 'doc':
        raise HTTPException(status_code=400, detail='Legacy .doc files are not supported. Please upload DOCX.')
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail='Unsupported file type')

    mime = (file.content_type or '').lower()
    if mime and mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail='Unsupported MIME type')


def _get_owned_document(
    db: Session,
    document_id: int,
    current_user: User,
) -> SummarizerDocument:
    document = db.query(SummarizerDocument).filter(SummarizerDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail='Document not found')
    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail='Access denied')
    return document


def _build_document_detail(db: Session, document: SummarizerDocument) -> SummarizerDocumentDetail:
    chunk_count = db.query(func.count(SummarizerChunk.id)).filter(SummarizerChunk.document_id == document.id).scalar() or 0
    message_count = (
        db.query(func.count(SummarizerMessage.id))
        .filter(SummarizerMessage.document_id == document.id)
        .scalar()
        or 0
    )
    return SummarizerDocumentDetail(
        id=document.id,
        owner_id=document.owner_id,
        original_name=document.original_name,
        mime_type=document.mime_type,
        size=document.size,
        status=document.status,
        error_text=document.error_text,
        summary_text=document.summary_text,
        summary_updated_at=document.summary_updated_at,
        created_at=document.created_at,
        chunk_count=chunk_count,
        message_count=message_count,
    )


@router.post('/documents/upload', response_model=SummarizerDocumentOut)
def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_csrf(request)
    _validate_upload_file(file)

    stored_name, size = store_upload_file(file)
    if size > settings.max_upload_bytes:
        delete_file(stored_name)
        raise HTTPException(status_code=400, detail=f'File too large. Max {settings.max_upload_mb}MB')

    document = SummarizerDocument(
        owner_id=current_user.id,
        filename=stored_name,
        original_name=file.filename or 'uploaded-file',
        mime_type=file.content_type or 'application/octet-stream',
        size=size,
        status=SummarizerDocumentStatus.uploaded,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    ingest_summarizer_document_task.delay(document.id)
    return document


@router.get('/documents', response_model=list[SummarizerDocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(SummarizerDocument)
        .filter(SummarizerDocument.owner_id == current_user.id)
        .order_by(SummarizerDocument.created_at.desc())
        .all()
    )


@router.get('/documents/{document_id}', response_model=SummarizerDocumentDetail)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = _get_owned_document(db, document_id, current_user)
    return _build_document_detail(db, document)


@router.delete('/documents/{document_id}')
def delete_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_csrf(request)
    document = _get_owned_document(db, document_id, current_user)
    filename = document.filename
    db.delete(document)
    db.commit()
    delete_file(filename)
    return {'message': 'Deleted'}


@router.post('/documents/{document_id}/summarize')
def summarize_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_csrf(request)
    enforce_chat_rate_limit(current_user.id)
    document = _get_owned_document(db, document_id, current_user)

    if document.status != SummarizerDocumentStatus.ready:
        raise HTTPException(status_code=400, detail='Document is not ready yet')

    query = 'Summarize the most important information in this document.'
    chunks = search_summarizer_chunks(
        db=db,
        document_id=document.id,
        question=query,
        top_k=max(settings.retrieval_top_k, 12),
    )
    if not chunks:
        raise HTTPException(status_code=400, detail='No indexed content available for summarization')

    provider = get_llm_provider(db)
    llm_messages = [{'role': 'user', 'content': query}]
    summary_text = ''.join(provider.stream_chat(_build_summary_prompt(), llm_messages, chunks)).strip()
    if not summary_text:
        raise HTTPException(status_code=500, detail='Summary generation failed')

    document.summary_text = summary_text
    document.summary_updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(document)
    return {
        'summary_text': document.summary_text,
        'summary_updated_at': document.summary_updated_at,
    }


@router.get('/documents/{document_id}/messages', response_model=list[SummarizerMessageOut])
def get_messages(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_document(db, document_id, current_user)
    return (
        db.query(SummarizerMessage)
        .filter(SummarizerMessage.document_id == document_id)
        .order_by(SummarizerMessage.created_at.asc())
        .all()
    )


@router.post('/documents/{document_id}/ask')
def ask_document(
    document_id: int,
    payload: SummarizerAskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enforce_chat_rate_limit(current_user.id)
    document = _get_owned_document(db, document_id, current_user)

    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail='Question is required')
    if document.status != SummarizerDocumentStatus.ready:
        raise HTTPException(status_code=400, detail='Document is not ready yet')

    user_message = SummarizerMessage(document_id=document.id, role=ChatRole.user, content=question)
    db.add(user_message)
    db.commit()

    chunks = search_summarizer_chunks(
        db=db,
        document_id=document.id,
        question=question,
    )
    _, _, low_confidence = retrieval_confidence(chunks)
    warning = LOW_CONFIDENCE_WARNING if low_confidence and chunks else None

    history = (
        db.query(SummarizerMessage)
        .filter(SummarizerMessage.document_id == document.id)
        .order_by(SummarizerMessage.created_at.asc())
        .limit(12)
        .all()
    )
    llm_messages = [{'role': msg.role.value, 'content': msg.content} for msg in history]
    sources = [_source_ref(chunk) for chunk in chunks]

    def stream():
        full_answer = ''
        try:
            if not chunks:
                fallback = (
                    'I cannot find enough relevant context in this uploaded document '
                    'to answer your question confidently. Please ask a more specific question.'
                )
                for token in fallback.split(' '):
                    part = token + ' '
                    full_answer += part
                    yield _event('token', {'text': part})
            else:
                provider = get_llm_provider(db)
                for token in provider.stream_chat(_build_document_chat_prompt(), llm_messages, chunks):
                    full_answer += token
                    yield _event('token', {'text': token})

            assistant_message = SummarizerMessage(
                document_id=document.id,
                role=ChatRole.assistant,
                content=full_answer.strip(),
            )
            db.add(assistant_message)
            db.commit()
            db.refresh(assistant_message)

            yield _event('sources', {'items': sources})
            yield _event(
                'done',
                {
                    'answer': full_answer.strip(),
                    'document_id': document.id,
                    'message_id': assistant_message.id,
                    'low_confidence': low_confidence,
                    'warning': warning,
                },
            )
        except Exception:
            db.rollback()
            yield _event('error', {'message': 'Unable to complete summarizer chat request'})

    return StreamingResponse(stream(), media_type='text/event-stream')
