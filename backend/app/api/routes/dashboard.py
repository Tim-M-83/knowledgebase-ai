from fastapi import APIRouter, Depends, Request
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.rbac import require_roles
from app.core.security import validate_csrf
from app.db.session import get_db
from app.models.chat import ChatMessage, ChatRole, ChatSession, ChatSessionType
from app.models.chunk import Chunk
from app.models.department import Department
from app.models.document import Document, DocumentTag, DocumentStatus
from app.models.retrieval_log import RetrievalLog
from app.models.tag import Tag
from app.models.user import Role, User
from app.schemas.dashboard import ChartsResponse, GapItem, KpisResponse, LabelValue, TimePoint


router = APIRouter(prefix='/dashboard', tags=['dashboard'])


@router.get('/kpis', response_model=KpisResponse)
def kpis(db: Session = Depends(get_db), _: User = Depends(require_roles(Role.admin, Role.editor))):
    chat_session_ids = select(ChatSession.id).where(ChatSession.session_type == ChatSessionType.chat)

    docs = db.query(func.count(Document.id)).scalar() or 0
    chunks = db.query(func.count(Chunk.id)).scalar() or 0
    users = db.query(func.count(User.id)).scalar() or 0
    chats = (
        db.query(func.count(ChatMessage.id))
        .filter(
            ChatMessage.role == ChatRole.user,
            ChatMessage.session_id.in_(chat_session_ids),
        )
        .scalar()
        or 0
    )
    failed = db.query(func.count(Document.id)).filter(Document.status == DocumentStatus.failed).scalar() or 0
    last_ingestion = db.query(func.max(Document.created_at)).scalar()

    return KpisResponse(
        docs=docs,
        chunks=chunks,
        users=users,
        chats=chats,
        last_ingestion=last_ingestion,
        failed_ingestions=failed,
    )


@router.get('/charts', response_model=ChartsResponse)
def charts(db: Session = Depends(get_db), _: User = Depends(require_roles(Role.admin, Role.editor))):
    chat_session_ids = select(ChatSession.id).where(ChatSession.session_type == ChatSessionType.chat)

    daily_rows = (
        db.query(func.date(ChatMessage.created_at), func.count(ChatMessage.id))
        .filter(
            ChatMessage.role == ChatRole.user,
            ChatMessage.session_id.in_(chat_session_ids),
        )
        .group_by(func.date(ChatMessage.created_at))
        .order_by(func.date(ChatMessage.created_at))
        .all()
    )

    top_tags_rows = (
        db.query(Tag.name, func.count(DocumentTag.document_id))
        .join(DocumentTag, DocumentTag.tag_id == Tag.id)
        .group_by(Tag.name)
        .order_by(desc(func.count(DocumentTag.document_id)))
        .limit(8)
        .all()
    )

    top_deps_rows = (
        db.query(Department.name, func.count(Document.id))
        .join(Document, Document.department_id == Department.id)
        .group_by(Department.name)
        .order_by(desc(func.count(Document.id)))
        .limit(8)
        .all()
    )

    unanswered_rows = (
        db.query(func.date(RetrievalLog.created_at), func.count(RetrievalLog.id))
        .filter(
            RetrievalLog.session_id.in_(chat_session_ids),
            (RetrievalLog.had_sources.is_(False)) | (RetrievalLog.low_confidence.is_(True)),
        )
        .group_by(func.date(RetrievalLog.created_at))
        .order_by(func.date(RetrievalLog.created_at))
        .all()
    )

    return ChartsResponse(
        daily_chats=[TimePoint(date=str(row[0]), value=row[1]) for row in daily_rows],
        top_tags=[LabelValue(label=row[0], value=row[1]) for row in top_tags_rows],
        top_departments=[LabelValue(label=row[0], value=row[1]) for row in top_deps_rows],
        unanswered_daily=[TimePoint(date=str(row[0]), value=row[1]) for row in unanswered_rows],
    )


@router.get('/gaps', response_model=list[GapItem])
def gaps(db: Session = Depends(get_db), _: User = Depends(require_roles(Role.admin, Role.editor))):
    chat_session_ids = select(ChatSession.id).where(ChatSession.session_type == ChatSessionType.chat)
    rows = (
        db.query(RetrievalLog)
        .filter(
            RetrievalLog.session_id.in_(chat_session_ids),
            (RetrievalLog.had_sources.is_(False)) | (RetrievalLog.low_confidence.is_(True)),
        )
        .order_by(RetrievalLog.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        GapItem(
            id=row.id,
            question=row.question,
            avg_score=row.avg_score,
            had_sources=row.had_sources,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.delete('/gaps')
def clear_gaps(
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin)),
):
    validate_csrf(request)
    chat_session_ids = select(ChatSession.id).where(ChatSession.session_type == ChatSessionType.chat)
    deleted = (
        db.query(RetrievalLog)
        .filter(
            RetrievalLog.session_id.in_(chat_session_ids),
            (RetrievalLog.had_sources.is_(False)) | (RetrievalLog.low_confidence.is_(True)),
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return {'deleted_gaps': deleted}
