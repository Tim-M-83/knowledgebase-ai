from __future__ import annotations

import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import get_settings


class UTCFormatter(logging.Formatter):
    converter = time.gmtime


class ServiceContextFilter(logging.Filter):
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, 'service'):
            record.service = self.service_name
        return True


def configure_app_logging(service_name: str) -> logging.Logger:
    settings = get_settings()
    level = getattr(logging, settings.app_log_level.upper(), logging.INFO)
    log_dir = Path(settings.app_log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger('app')
    if getattr(logger, '_kbai_logging_service', None) == service_name and logger.handlers:
        return logger

    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
    logger.setLevel(level)
    logger.propagate = False

    formatter = UTCFormatter(
        fmt='%(asctime)s %(levelname)s [%(service)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%SZ',
    )
    context_filter = ServiceContextFilter(service_name)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(context_filter)

    file_handler = RotatingFileHandler(
        log_dir / f'{service_name}.log',
        maxBytes=max(settings.app_log_max_bytes, 1024),
        backupCount=max(settings.app_log_backup_count, 1),
        encoding='utf-8',
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(context_filter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    logger._kbai_logging_service = service_name  # type: ignore[attr-defined]
    return logger
