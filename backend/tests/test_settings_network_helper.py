from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes import settings
from app.core.rbac import require_roles
from app.models.user import Role
from app.schemas.settings import NetworkHelperUpdate


def test_get_network_helper_returns_saved_override(monkeypatch):
    monkeypatch.setattr(settings, '_get_network_helper_lan_host', lambda _db: '192.168.1.50')

    out = settings.get_network_helper_settings(
        db=object(),
        _=SimpleNamespace(id=1, role=Role.admin),
    )

    assert out.lan_host_override == '192.168.1.50'


def test_update_network_helper_saves_valid_override(monkeypatch):
    flags = {'csrf': False, 'saved': None}

    monkeypatch.setattr(settings, 'validate_csrf', lambda _request: flags.__setitem__('csrf', True))
    monkeypatch.setattr(settings, 'set_runtime_setting', lambda _db, key, value: flags.__setitem__('saved', (key, value)))

    out = settings.update_network_helper_settings(
        payload=NetworkHelperUpdate(lan_host_override='192.168.1.50'),
        request=object(),
        db=object(),
        current_user=SimpleNamespace(id=1, role=Role.admin),
    )

    assert flags['csrf'] is True
    assert flags['saved'] == (settings.KEY_NETWORK_HELPER_LAN_HOST, '192.168.1.50')
    assert out.lan_host_override == '192.168.1.50'


def test_update_network_helper_clears_override(monkeypatch):
    flags = {'csrf': False, 'deleted': None}

    monkeypatch.setattr(settings, 'validate_csrf', lambda _request: flags.__setitem__('csrf', True))
    monkeypatch.setattr(settings, 'delete_runtime_setting', lambda _db, key: flags.__setitem__('deleted', key))

    out = settings.update_network_helper_settings(
        payload=NetworkHelperUpdate(lan_host_override=''),
        request=object(),
        db=object(),
        current_user=SimpleNamespace(id=1, role=Role.admin),
    )

    assert flags['csrf'] is True
    assert flags['deleted'] == settings.KEY_NETWORK_HELPER_LAN_HOST
    assert out.lan_host_override is None


@pytest.mark.parametrize(
    ('candidate', 'expected_detail'),
    [
        ('http://192.168.1.50', 'full URL'),
        ('   ', 'whitespace only'),
        ('localhost', 'localhost'),
        ('bad/host', 'full URL'),
    ],
)
def test_update_network_helper_rejects_invalid_hosts(candidate, expected_detail):
    with pytest.raises(HTTPException) as exc:
        settings._normalize_network_helper_lan_host(candidate)

    assert exc.value.status_code == 400
    assert expected_detail in str(exc.value.detail)


def test_network_helper_endpoint_is_admin_only():
    checker = require_roles(Role.admin)
    with pytest.raises(HTTPException) as exc:
        checker(current_user=SimpleNamespace(role=Role.editor))
    assert exc.value.status_code == 403
