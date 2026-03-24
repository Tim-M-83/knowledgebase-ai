from app.tasks.celery_app import celery_app


def test_ingestion_task_is_registered():
    assert 'ingest_document' in celery_app.tasks
