"""Secure video file storage.

Handles filename sanitization, MIME/extension validation, and size limits.
Uploaded files are stored under the configured upload directory using a random
UUID name; the original user filename is preserved only on the Video record.
"""

from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm", ".mpeg", ".mpg"}
_FILENAME_SANITIZE = re.compile(r"[^\w.\-]+")


class UploadValidationError(Exception):
    """Raised when an uploaded file is rejected."""


class StorageService:
    """Manages upload persistence under ``settings.upload_dir``."""

    def __init__(self, upload_dir: Path | None = None) -> None:
        self.upload_dir = upload_dir or settings.upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def _validate(self, mime_type: str, filename: str, size: int) -> None:
        if size <= 0:
            raise UploadValidationError("Uploaded file is empty")
        if size > settings.max_upload_bytes:
            raise UploadValidationError("File exceeds the maximum allowed size")
        if mime_type not in settings.allowed_video_mime_types:
            raise UploadValidationError(f"Unsupported media type: {mime_type}")

        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise UploadValidationError(f"Unsupported file extension: {suffix or '(none)'}")

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        name = Path(filename).name  # strip any directory components
        name = _FILENAME_SANITIZE.sub("_", name)
        name = re.sub(r"_+", "_", name).strip(" _")
        return name[:200] or "upload"

    def save_upload(self, data: bytes, mime_type: str, original_name: str) -> Path:
        """Validate and persist an uploaded file, returning its stored path."""
        self._validate(mime_type, original_name, len(data))
        safe_name = self.sanitize_filename(original_name)
        suffix = Path(safe_name).suffix.lower() or ".mp4"
        stored_name = f"{uuid4().hex}{suffix}"
        destination = self.upload_dir / stored_name

        destination.write_bytes(data)
        logger.info("Stored upload %s (%s bytes)", stored_name, len(data))
        return destination

    def resolve(self, filename: str) -> Path:
        path = (self.upload_dir / filename).resolve()
        if not path.is_relative_to(self.upload_dir.resolve()):
            raise UploadValidationError("Invalid storage path")
        if not path.exists():
            raise FileNotFoundError(f"Stored file not found: {filename}")
        return path

    def delete(self, filename: str) -> None:
        path = self.resolve(filename)
        path.unlink(missing_ok=True)
        logger.info("Deleted stored file %s", filename)


storage_service = StorageService()
