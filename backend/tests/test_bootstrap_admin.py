from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.department import Department
from app.models.user import Role, User
from app.services import bootstrap_admin


def _session_factory():
    engine = create_engine('sqlite:///:memory:')
    Department.__table__.create(engine)
    User.__table__.create(engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def test_ensure_bootstrap_admin_creates_first_admin(monkeypatch):
    Session = _session_factory()
    monkeypatch.setattr(bootstrap_admin, 'generate_bootstrap_password', lambda: 'bootstrap-password')

    with Session() as db:
        creds = bootstrap_admin.ensure_bootstrap_admin(db)
        user = db.query(User).filter(User.role == Role.admin).first()

    assert creds is not None
    assert creds.email == 'admin@local'
    assert creds.password == 'bootstrap-password'
    assert user is not None
    assert user.email == 'admin@local'
    assert user.must_change_credentials is True
    assert user.is_bootstrap_admin is True


def test_ensure_bootstrap_admin_is_idempotent(monkeypatch):
    Session = _session_factory()
    monkeypatch.setattr(bootstrap_admin, 'generate_bootstrap_password', lambda: 'first-password')

    with Session() as db:
        first = bootstrap_admin.ensure_bootstrap_admin(db)
        second = bootstrap_admin.ensure_bootstrap_admin(db)
        count = db.query(User).filter(User.role == Role.admin).count()

    assert first is not None
    assert second is None
    assert count == 1


def test_ensure_bootstrap_admin_does_nothing_when_admin_exists(monkeypatch):
    Session = _session_factory()
    monkeypatch.setattr(bootstrap_admin, 'generate_bootstrap_password', lambda: 'should-not-be-used')

    with Session() as db:
        db.add(
            User(
                email='owner@example.com',
                password_hash='hash',
                role=Role.admin,
                must_change_credentials=False,
                is_bootstrap_admin=False,
            )
        )
        db.commit()

        creds = bootstrap_admin.ensure_bootstrap_admin(db)
        count = db.query(User).filter(User.role == Role.admin).count()

    assert creds is None
    assert count == 1
