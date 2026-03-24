from __future__ import annotations

import io
import re
import zipfile
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import get_settings


TIMESTAMP_RE = re.compile(r'^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s')
REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r'(Bearer\s+)[A-Za-z0-9._-]+'), r'\1[REDACTED]'),
    (re.compile(r'(Authorization:\s*Bearer\s+)[A-Za-z0-9._-]+', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'((?:license|api|openai)_key\s*[=:]\s*)[^\s,]+', re.IGNORECASE), r'\1[REDACTED]'),
)
SERVICE_NAMES = ('api', 'worker')


class LogExportUnavailableError(ValueError):
    pass


@dataclass
class LogEntry:
    timestamp: datetime
    lines: list[str]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _sanitize_line(line: str) -> str:
    sanitized = line
    for pattern, replacement in REDACTIONS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def _log_files(service_name: str) -> list[Path]:
    settings = get_settings()
    log_dir = Path(settings.app_log_dir)
    if not log_dir.exists():
        return []
    return sorted(
        [path for path in log_dir.glob(f'{service_name}.log*') if path.is_file()],
        key=lambda path: path.stat().st_mtime,
    )


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _read_entries(service_name: str) -> list[LogEntry]:
    entries: list[LogEntry] = []
    current_timestamp: datetime | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_timestamp, current_lines
        if current_timestamp is not None and current_lines:
            entries.append(LogEntry(timestamp=current_timestamp, lines=current_lines))
        current_timestamp = None
        current_lines = []

    for path in _log_files(service_name):
        content = path.read_text(encoding='utf-8', errors='ignore').splitlines()
        for raw_line in content:
            line = _sanitize_line(raw_line.rstrip('\n'))
            match = TIMESTAMP_RE.match(line)
            if match:
                flush()
                current_timestamp = _parse_timestamp(match.group('ts'))
                current_lines = [line] if current_timestamp is not None else []
                continue

            if current_lines:
                current_lines.append(line)

    flush()
    return entries


def _bounded_recent_entries(entries: list[LogEntry]) -> list[LogEntry]:
    settings = get_settings()
    cutoff = _utcnow() - timedelta(hours=max(settings.app_log_export_window_hours, 1))
    max_lines = max(settings.app_log_export_max_lines, 1)
    filtered = [entry for entry in entries if entry.timestamp >= cutoff]

    kept: deque[LogEntry] = deque()
    line_count = 0

    for entry in reversed(filtered):
        entry_lines = len(entry.lines)
        if entry_lines > max_lines and not kept:
            kept.appendleft(LogEntry(timestamp=entry.timestamp, lines=entry.lines[-max_lines:]))
            break
        if line_count + entry_lines > max_lines:
            break
        kept.appendleft(entry)
        line_count += entry_lines

    return list(kept)


def _render_entries(entries: list[LogEntry]) -> str:
    rendered = '\n'.join(line for entry in entries for line in entry.lines)
    if rendered:
        return f'{rendered}\n'
    return ''


def build_support_log_export() -> tuple[bytes, str]:
    settings = get_settings()
    exported_at = _utcnow()
    archive_buffer = io.BytesIO()
    included_files = 0

    with zipfile.ZipFile(archive_buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            'README.txt',
            (
                'KnowledgeBase AI support log export\n'
                f'Exported at: {exported_at.strftime("%Y-%m-%dT%H:%M:%SZ")}\n'
                f'Included services: {", ".join(SERVICE_NAMES)}\n'
                f'Window: last {max(settings.app_log_export_window_hours, 1)} hours\n'
                f'Max lines per service: {max(settings.app_log_export_max_lines, 1)}\n'
                'Sensitive values such as tokens and keys are redacted where possible.\n'
            ),
        )

        for service_name in SERVICE_NAMES:
            entries = _bounded_recent_entries(_read_entries(service_name))
            if not entries:
                continue
            archive.writestr(f'{service_name}.log', _render_entries(entries))
            included_files += 1

    if included_files == 0:
        raise LogExportUnavailableError('No recent application logs are available for export.')

    filename = f'kbai-support-logs-{exported_at.strftime("%Y%m%dT%H%M%SZ")}.zip'
    return archive_buffer.getvalue(), filename
