import json
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_current_user, validate_csrf
from app.db.session import get_db
from app.models.chat import ChatMessage, ChatRole, ChatSession, ChatSessionType
from app.models.chat_message_source import ChatMessageSource
from app.models.feedback import Feedback
from app.models.retrieval_log import RetrievalLog
from app.models.user import User
from app.schemas.chat import (
    ChatAskRequest,
    ChatMessageOut,
    ChatSessionCreate,
    ChatSessionOut,
    FeedbackCreate,
)
from app.services.llm import get_llm_provider
from app.services.retrieval import retrieval_confidence, search_chunks
from app.utils.rate_limit import enforce_chat_rate_limit


router = APIRouter(prefix='/chat', tags=['chat'])
settings = get_settings()
LOW_CONFIDENCE_WARNING = (
    'Answer generated with low retrieval confidence. Verify against sources and consider refining your question.'
)


def chat_warning(has_sources: bool, low_confidence: bool) -> str | None:
    if has_sources and low_confidence:
        return LOW_CONFIDENCE_WARNING
    return None


def build_system_prompt() -> str:
    return (
        'You are a retrieval assistant for internal knowledge. '
        'Only answer from provided sources. If evidence is insufficient, say so clearly. '
        'Cite statements using numeric references like [1], [2].\n\n'
        'Always return Markdown with this exact section order:\n'
        '## Direct Answer\n'
        '## Key Points\n'
        '## Evidence\n'
        '## Limitations (only when needed)\n\n'
        'Formatting rules:\n'
        '- Use short paragraphs.\n'
        '- Use bullet lists for facts or steps.\n'
        '- Do not use tables unless the user asks for a table.\n'
        '- If the answer is unknown, state that clearly under "## Direct Answer".\n'
        '- Keep citations inline, for example: "The service includes rapid prototyping [1]".'
    )


def _source_ref_from_row(row: ChatMessageSource) -> dict:
    return {
        'id': row.source_order,
        'document_id': row.document_id,
        'original_name': row.original_name,
        'chunk_id': row.chunk_id,
        'score': row.score,
        'page_number': row.page_number,
        'csv_row_start': row.csv_row_start,
        'csv_row_end': row.csv_row_end,
        'snippet': row.snippet,
    }


@router.post('/sessions', response_model=ChatSessionOut)
def create_session(
    payload: ChatSessionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_csrf(request)
    session = ChatSession(
        user_id=current_user.id,
        title=payload.title or 'New Chat',
        session_type=ChatSessionType.chat,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get('/sessions', response_model=list[ChatSessionOut])
def list_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(ChatSession)
        .filter(
            ChatSession.user_id == current_user.id,
            ChatSession.session_type == ChatSessionType.chat,
        )
        .order_by(ChatSession.created_at.desc())
        .all()
    )


@router.delete('/sessions')
def clear_sessions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_csrf(request)
    deleted = (
        db.query(ChatSession)
        .filter(
            ChatSession.user_id == current_user.id,
            ChatSession.session_type == ChatSessionType.chat,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return {'deleted_sessions': deleted}


@router.get('/sessions/{session_id}', response_model=list[ChatMessageOut])
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    if session.user_id != current_user.id or session.session_type != ChatSessionType.chat:
        raise HTTPException(status_code=403, detail='Access denied')
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    assistant_ids = [msg.id for msg in messages if msg.role == ChatRole.assistant]
    source_map: dict[int, list[dict]] = defaultdict(list)
    if assistant_ids:
        source_rows = (
            db.query(ChatMessageSource)
            .filter(ChatMessageSource.message_id.in_(assistant_ids))
            .order_by(ChatMessageSource.message_id.asc(), ChatMessageSource.source_order.asc())
            .all()
        )
        for row in source_rows:
            source_map[row.message_id].append(_source_ref_from_row(row))

    return [
        ChatMessageOut(
            id=msg.id,
            session_id=msg.session_id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at,
            sources=source_map.get(msg.id, []),
        )
        for msg in messages
    ]


@router.post('/ask')
def ask(
    payload: ChatAskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enforce_chat_rate_limit(current_user.id)

    session: ChatSession | None = None
    if payload.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail='Session not found')
        if session.user_id != current_user.id or session.session_type != ChatSessionType.chat:
            raise HTTPException(status_code=403, detail='Access denied')
    else:
        session = ChatSession(
            user_id=current_user.id,
            title=payload.question[:64],
            session_type=ChatSessionType.chat,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    user_message = ChatMessage(session_id=session.id, role=ChatRole.user, content=payload.question)
    db.add(user_message)
    db.commit()

    filters = payload.filters
    results = search_chunks(
        db=db,
        user=current_user,
        question=payload.question,
        department_id=filters.department_id if filters else None,
        tag_ids=filters.tag_ids if filters else None,
    )
    _, avg_score, low_confidence = retrieval_confidence(results)

    system_prompt = build_system_prompt()

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(12)
        .all()
    )
    llm_messages = [{'role': msg.role.value, 'content': msg.content} for msg in history]

    sources = [
        {
            'id': r['id'],
            'document_id': r['document_id'],
            'original_name': r['original_name'],
            'chunk_id': r['chunk_id'],
            'score': r['score'],
            'page_number': (r['metadata'] or {}).get('page_number'),
            'csv_row_start': (r['metadata'] or {}).get('csv_row_start'),
            'csv_row_end': (r['metadata'] or {}).get('csv_row_end'),
            'snippet': r['snippet'],
        }
        for r in results
    ]

    def event(event_name: str, data: dict) -> str:
        return f"event: {event_name}\ndata: {json.dumps(data)}\n\n"

    def stream():
        full_answer = ''
        warning = chat_warning(has_sources=bool(results), low_confidence=low_confidence)
        try:
            if not results:
                fallback = (
                    '## Direct Answer\n'
                    'Not enough reliable sources were found to answer this question confidently.\n\n'
                    '## Key Points\n'
                    '- Refine your question to be more specific.\n'
                    '- Ensure relevant documents are indexed and in status "ready".\n'
                    '- Upload additional documents if needed.\n\n'
                    '## Evidence\n'
                    '- No sufficiently reliable sources were retrieved for this request.'
                )
                for token in fallback.split(' '):
                    part = token + ' '
                    full_answer += part
                    yield event('token', {'text': part})
            else:
                provider = get_llm_provider(db)
                for token in provider.stream_chat(system_prompt, llm_messages, results):
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

            if sources:
                for source in sources:
                    db.add(
                        ChatMessageSource(
                            message_id=assistant_message.id,
                            source_order=int(source['id']),
                            document_id=source['document_id'],
                            original_name=source['original_name'],
                            chunk_id=source['chunk_id'],
                            score=source['score'],
                            page_number=source.get('page_number'),
                            csv_row_start=source.get('csv_row_start'),
                            csv_row_end=source.get('csv_row_end'),
                            snippet=source['snippet'],
                        )
                    )

            log = RetrievalLog(
                session_id=session.id,
                question=payload.question,
                top_k=settings.retrieval_top_k,
                avg_score=avg_score,
                had_sources=bool(results),
                low_confidence=low_confidence,
            )
            db.add(log)
            db.commit()

            yield event('sources', {'items': sources})
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
            yield event('error', {'message': 'Unable to complete chat request'})

    return StreamingResponse(stream(), media_type='text/event-stream')


@router.post('/feedback')
def create_feedback(
    payload: FeedbackCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_csrf(request)
    message = db.query(ChatMessage).filter(ChatMessage.id == payload.message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail='Assistant message not found')

    session = db.query(ChatSession).filter(ChatSession.id == message.session_id).first()
    if not session or session.user_id != current_user.id or session.session_type != ChatSessionType.chat:
        raise HTTPException(status_code=403, detail='Access denied')

    item = Feedback(message_id=payload.message_id, rating=payload.rating, comment=payload.comment)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {'message': 'Feedback recorded'}
