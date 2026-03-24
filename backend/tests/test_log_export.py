from __future__ import annotations

import io
from datetime import datetime, timezone
from types import SimpleNamespace
import zipfile

import pytest
from fastapi import HTTPException

from app.api.routes import settings as settings_routes
from app.core import logging_setup
from app.models.user import Role
from app.services import log_export
from app.services.log_export import LogExportUnavailableError


def test_configure_app_logging_writes_service_log(tmp_path, monkeypatch):
    monkeypatch.setattr(
        logging_setup,
        'get_settings',
        lambda: SimpleNamespace(
            app_log_dir=str(tmp_path),
            app_log_level='INFO',
            app_log_max_bytes=1024,
            app_log_backup_count=2,
        ),
    )

    logger = logging_setup.configure_app_logging('api')
    try:
        logger.info('Support log smoke test')
        for handler in logger.handlers:
            handler.flush()
        content = (tmp_path / 'api.log').read_text(encoding='utf-8')
        assert 'Support log smoke test' in content
        assert '[api]' in content
    finally:
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
        if hasattr(logger, '_kbai_logging_service'):
            delattr(logger, '_kbai_logging_service')


def test_build_support_log_export_includes_recent_entries_and_redacts(tmp_path, monkeypatch):
    monkeypatch.setattr(
        log_export,
        'get_settings',
        lambda: SimpleNamespace(
            app_log_dir=str(tmp_path),
            app_log_export_window_hours=72,
            app_log_export_max_lines=10,
        ),
    )
    monkeypatch.setattr(
        log_export,
        '_utcnow',
        lambda: datetime(2026, 3, 24, 12, 0, tzinfo=timezone.utc),
    )

    (tmp_path / 'api.log').write_text(
        '2026-03-24T11:00:00Z INFO [api] app.api.routes.auth: Bearer token-123 license_key=polar_abc\n'
        '2026-03-20T11:00:00Z INFO [api] app.api.routes.auth: too old\n',
        encoding='utf-8',
    )
    (tmp_path / 'worker.log').write_text(
        '2026-03-24T10:00:00Z ERROR [worker] app.services.ingestion_service: boom\n'
        'Traceback (most recent call last):\n'
        '  example stack line\n',
        encoding='utf-8',
    )

    archive_bytes, filename = log_export.build_support_log_export()

    assert filename.startswith('kbai-support-logs-')

    with zipfile.ZipFile(io.BytesIO(archive_bytes), 'r') as archive:
        assert set(archive.namelist()) == {'README.txt', 'api.log', 'worker.log'}
        api_log = archive.read('api.log').decode('utf-8')
        worker_log = archive.read('worker.log').decode('utf-8')

    assert 'too old' not in api_log
    assert 'Bearer [REDACTED]' in api_log
    assert 'license_key=[REDACTED]' in api_log
    assert 'token-123' not in api_log
    assert 'Traceback (most recent call last):' in worker_log


def test_build_support_log_export_raises_when_no_recent_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(
        log_export,
        'get_settings',
        lambda: SimpleNamespace(
            app_log_dir=str(tmp_path),
            app_log_export_window_hours=72,
            app_log_export_max_lines=10,
        ),
    )
    monkeypatch.setattr(
        log_export,
        '_utcnow',
        lambda: datetime(2026, 3, 24, 12, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(LogExportUnavailableError):
        log_export.build_support_log_export()


def test_export_support_logs_returns_zip_response(monkeypatch):
    monkeypatch.setattr(settings_routes, 'build_support_log_export', lambda: (b'zip-bytes', 'logs.zip'))

    response = settings_routes.export_support_logs(
        current_user=SimpleNamespace(id=7, role=Role.admin),
    )

    assert response.media_type == 'application/zip'
    assert response.body == b'zip-bytes'
    assert response.headers['content-disposition'] == 'attachment; filename="logs.zip"'


def test_export_support_logs_maps_missing_logs_to_404(monkeypatch):
    monkeypatch.setattr(
        settings_routes,
        'build_support_log_export',
        lambda: (_ for _ in ()).throw(LogExportUnavailableError('No recent application logs are available for export.')),
    )

    with pytest.raises(HTTPException) as exc:
        settings_routes.export_support_logs(current_user=SimpleNamespace(id=8, role=Role.admin))

    assert exc.value.status_code == 404
