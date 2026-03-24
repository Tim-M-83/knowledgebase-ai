from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.summarizer import SummarizerChunk
from app.services.embeddings import get_embeddings_provider


settings = get_settings()


def search_summarizer_chunks(
    db: Session,
    document_id: int,
    question: str,
    top_k: int | None = None,
) -> list[dict]:
    provider = get_embeddings_provider(db)
    qvec = provider.embed_text(question)
    top_k = top_k or settings.retrieval_top_k

    distance = SummarizerChunk.embedding.cosine_distance(qvec)
    score = (1 - distance).label('score')

    stmt = (
        select(
            SummarizerChunk.id,
            SummarizerChunk.content,
            SummarizerChunk.meta,
            score,
        )
        .where(SummarizerChunk.document_id == document_id)
        .order_by(desc(score))
        .limit(top_k)
    )

    rows = db.execute(stmt).all()
    return [
        {
            'id': idx + 1,
            'chunk_id': row.id,
            'document_id': document_id,
            'content': row.content,
            'metadata': row.meta,
            'score': float(row.score),
            'snippet': (row.meta or {}).get('snippet', row.content[:200]),
        }
        for idx, row in enumerate(rows)
    ]
