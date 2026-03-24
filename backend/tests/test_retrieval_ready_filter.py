from app.models.user import Role
from app.services import retrieval


class DummyProvider:
    def embed_text(self, text: str) -> list[float]:
        return [0.0] * 3


class DummyResult:
    def all(self):
        return []


class DummySession:
    def __init__(self):
        self.stmt = None

    def execute(self, stmt):
        self.stmt = stmt
        return DummyResult()


class DummyUser:
    def __init__(self):
        self.role = Role.admin
        self.id = 1
        self.department_id = None


def test_search_chunks_filters_ready_documents(monkeypatch):
    monkeypatch.setattr(retrieval, 'get_embeddings_provider', lambda db: DummyProvider())
    db = DummySession()
    retrieval.search_chunks(db=db, user=DummyUser(), question='What is this?')
    where_sql = ' '.join(str(criteria) for criteria in db.stmt._where_criteria)
    assert 'documents.status' in where_sql
