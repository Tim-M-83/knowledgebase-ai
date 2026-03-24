import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.security import get_current_user, validate_csrf
from app.db.session import get_db
from app.models.chat import ChatMessage, ChatRole, ChatSession, ChatSessionType
from app.models.user import User
from app.schemas.chat import ChatMessageOut, ChatSessionCreate, ChatSessionOut, EmailHelperAskRequest
from app.services.feature_flags import get_email_helper_enabled
from app.services.llm import get_llm_provider
from app.services.retrieval import retrieval_confidence, search_chunks
from app.utils.rate_limit import enforce_chat_rate_limit


router = APIRouter(prefix='/email-helper', tags=['email-helper'])


def _require_email_helper_enabled(db: Session) -> None:
    if not get_email_helper_enabled(db):
        raise HTTPException(status_code=403, detail='Email Helper is disabled by admin')


def _build_system_prompt() -> str:
    return (
        'You are an internal email reply assistant. '
        'Use only the provided internal context as knowledge source. '
        'Write a ready-to-send reply email in plain text.\n\n'
        'Output constraints:\n'
        '- Return only the final email response text.\n'
        '- Do not include analysis, reasoning, section headers, markdown, citations, or bullet lists.\n'
        '- Keep tone professional, concise, and helpful.\n'
        '- If context is insufficient, write a polite reply asking for the missing details.'
    )


@router.post('/sessions', response_model=ChatSessionOut)
def create_session(
    payload: ChatSessionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_csrf(request)
    _require_email_helper_enabled(db)
    session = ChatSession(
        user_id=current_user.id,
        title=payload.title or 'New Email Reply',
        session_type=ChatSessionType.email_helper,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get('/sessions', response_model=list[ChatSessionOut])
def list_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_email_helper_enabled(db)
    return (
        db.query(ChatSession)
        .filter(
            ChatSession.user_id == current_user.id,
            ChatSession.session_type == ChatSessionType.email_helper,
        )
        .order_by(ChatSession.created_at.desc())
        .all()
    )


@router.get('/sessions/{session_id}', response_model=list[ChatMessageOut])
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_email_helper_enabled(db)
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    if session.user_id != current_user.id or session.session_type != ChatSessionType.email_helper:
        raise HTTPException(status_code=403, detail='Access denied')

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return [
        ChatMessageOut(
            id=msg.id,
            session_id=msg.session_id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at,
            sources=[],
        )
        for msg in messages
    ]


@router.delete('/sessions/{session_id}')
def delete_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_csrf(request)
    _require_email_helper_enabled(db)
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    if session.user_id != current_user.id or session.session_type != ChatSessionType.email_helper:
        raise HTTPException(status_code=403, detail='Access denied')

    db.delete(session)
    db.commit()
    return {'message': 'Deleted'}


@router.post('/ask')
def ask(
    payload: EmailHelperAskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_email_helper_enabled(db)
    enforce_chat_rate_limit(current_user.id)

    session: ChatSession | None = None
    if payload.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail='Session not found')
        if session.user_id != current_user.id or session.session_type != ChatSessionType.email_helper:
            raise HTTPException(status_code=403, detail='Access denied')
    else:
        session = ChatSession(
            user_id=current_user.id,
            title=payload.email_text[:64] or 'New Email Reply',
            session_type=ChatSessionType.email_helper,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    user_message = ChatMessage(session_id=session.id, role=ChatRole.user, content=payload.email_text)
    db.add(user_message)
    db.commit()

    results = search_chunks(
        db=db,
        user=current_user,
        question=payload.email_text,
    )
    _, _, low_confidence = retrieval_confidence(results)

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(12)
        .all()
    )
    llm_messages = [{'role': msg.role.value, 'content': msg.content} for msg in history]

    def event(event_name: str, data: dict) -> str:
        return f"event: {event_name}\ndata: {json.dumps(data)}\n\n"

    def stream():
        full_answer = ''
        warning = (
            'Generated with limited confidence. Please review before sending.'
            if low_confidence
            else None
        )
        try:
            if not results:
                fallback = (
                    'Hi,\\n\\n'
                    'Thank you for your email. I want to provide an accurate answer, '
                    'but I currently do not have enough verified internal context to respond fully. '
                    'Could you please share a bit more detail so I can help you properly?\\n\\n'
                    'Best regards,'
                )
                for token in fallback.split(' '):
                    part = token + ' '
                    full_answer += part
                    yield event('token', {'text': part})
            else:
                provider = get_llm_provider(db)
                for token in provider.stream_chat(_build_system_prompt(), llm_messages, results):
                    full_answer += token
                    yield event('token', {'text': token})

            assistant_message = ChatMessage(
                session_id=session.id,
                role=ChatRole.assistant,
                content=full_answer.strip(),
            )
            db.add(assistant_message)
            db.commit()
            db.refresh(assistant_message)

            yield event(
                'done',
                {
                    'answer': full_answer.strip(),
                    'session_id': session.id,
                    'message_id': assistant_message.id,
                    'low_confidence': low_confidence,
                    'warning': warning,
                },
            )
        except Exception:
            db.rollback()
            yield event('error', {'message': 'Unable to complete email helper request'})

    return StreamingResponse(stream(), media_type='text/event-stream')
