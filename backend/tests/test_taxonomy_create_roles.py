import pytest
from fastapi import HTTPException

from app.core.rbac import require_roles
from app.models.user import Role


class DummyUser:
    def __init__(self, role: Role):
        self.role = role


def test_admin_and_editor_allowed_for_taxonomy_create():
    checker = require_roles(Role.admin, Role.editor)
    assert checker(current_user=DummyUser(Role.admin)).role == Role.admin
    assert checker(current_user=DummyUser(Role.editor)).role == Role.editor


def test_viewer_denied_for_taxonomy_create():
    checker = require_roles(Role.admin, Role.editor)
    with pytest.raises(HTTPException) as exc:
        checker(current_user=DummyUser(Role.viewer))
    assert exc.value.status_code == 403
