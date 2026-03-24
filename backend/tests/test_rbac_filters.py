import pytest

from app.core.rbac import ensure_can_access_document
from app.models.document import DocumentVisibility
from app.models.user import Role


class DummyDoc:
    def __init__(self, visibility, owner_id, department_id=None):
        self.visibility = visibility
        self.owner_id = owner_id
        self.department_id = department_id


class DummyUser:
    def __init__(self, role, user_id, department_id=None):
        self.role = role
        self.id = user_id
        self.department_id = department_id


def test_admin_can_access_any_document():
    user = DummyUser(Role.admin, user_id=1)
    doc = DummyDoc(DocumentVisibility.private, owner_id=2)
    ensure_can_access_document(doc, user)


def test_department_visibility_requires_match():
    user = DummyUser(Role.viewer, user_id=1, department_id=10)
    doc = DummyDoc(DocumentVisibility.department, owner_id=2, department_id=10)
    ensure_can_access_document(doc, user)


def test_private_visibility_requires_owner():
    user = DummyUser(Role.viewer, user_id=1)
    doc = DummyDoc(DocumentVisibility.private, owner_id=2)
    with pytest.raises(Exception):
        ensure_can_access_document(doc, user)
