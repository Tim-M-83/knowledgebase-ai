from pathlib import Path
import shutil
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings


settings = get_settings()


def ensure_storage_path() -> Path:
    path = Path(settings.file_storage_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def store_upload_file(upload_file: UploadFile) -> tuple[str, int]:
    storage_path = ensure_storage_path()
    ext = upload_file.filename.split('.')[-1].lower()
    unique_name = f'{uuid4().hex}.{ext}'
    target = storage_path / unique_name

    with target.open('wb') as out_file:
        shutil.copyfileobj(upload_file.file, out_file)

    size = target.stat().st_size
    return unique_name, size


def load_file_path(filename: str) -> Path:
    path = ensure_storage_path() / filename
    if not path.exists():
        raise FileNotFoundError(f'File {filename} not found in storage')
    return path


def delete_file(filename: str) -> None:
    path = ensure_storage_path() / filename
    if path.exists():
        path.unlink(missing_ok=True)
