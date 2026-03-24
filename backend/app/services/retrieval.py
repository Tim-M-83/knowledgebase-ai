from sqlalchemy import Select, desc, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus, DocumentTag, DocumentVisibility
from app.models.user import Role, User
from app.services.embeddings import get_embeddings_provider


settings = get_settings()


def _visibility_filters(user: User):
    if user.role == Role.admin:
        return True

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
    return filters


def search_chunks(
    db: Session,
    user: User,
    question: str,
    top_k: int | None = None,
    department_id: int | None = None,
    tag_ids: list[int] | None = None,
) -> list[dict]:
    provider = get_embeddings_provider(db)
    qvec = provider.embed_text(question)
    top_k = top_k or settings.retrieval_top_k

    distance = Chunk.embedding.cosine_distance(qvec)
    score = (1 - distance).label('score')

    stmt: Select = (
        select(
            Chunk.id,
            Chunk.document_id,
            Chunk.content,
            Chunk.meta,
            Document.original_name,
            score,
        )
        .join(Document, Document.id == Chunk.document_id)
        .where(Document.status == DocumentStatus.ready)
        .order_by(desc(score))
        .limit(top_k)
    )

    visibility = _visibility_filters(user)
    if visibility is not True:
        from sqlalchemy import or_

        stmt = stmt.where(or_(*visibility))

    if department_id:
        stmt = stmt.where(Document.department_id == department_id)

    if tag_ids:
        stmt = stmt.join(DocumentTag, DocumentTag.document_id == Document.id).where(DocumentTag.tag_id.in_(tag_ids))

    rows = db.execute(stmt).all()
    return [
        {
            'id': idx + 1,
            'chunk_id': row.id,
            'document_id': row.document_id,
            'content': row.content,
            'metadata': row.meta,
            'original_name': row.original_name,
            'score': float(row.score),
            'snippet': (row.meta or {}).get('snippet', row.content[:200]),
        }
        for idx, row in enumerate(rows)
    ]


def retrieval_confidence(results: list[dict]) -> tuple[float, float, bool]:
    if not results:
        return 0.0, 0.0, True
    scores = [item['score'] for item in results]
    max_score = max(scores)
    top3 = scores[:3]
    avg_top3 = sum(top3) / len(top3)
    low = avg_top3 < settings.retrieval_low_conf_threshold
    return max_score, avg_top3, low
