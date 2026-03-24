from app.db.session import SessionLocal
from app.services.ingestion_service import ingest_document
from app.services.summarizer_ingestion_service import ingest_summarizer_document
from app.tasks.celery_app import celery_app


@celery_app.task(name='ingest_document')
def ingest_document_task(document_id: int):
    db = SessionLocal()
    try:
        return ingest_document(db, document_id)
    finally:
        db.close()


@celery_app.task(name='ingest_summarizer_document')
def ingest_summarizer_document_task(document_id: int):
    db = SessionLocal()
    try:
        return ingest_summarizer_document(db, document_id)
    finally:
        db.close()
