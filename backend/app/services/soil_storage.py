"""Secure storage of uploaded soil report documents.

Rules enforced here:

- only PDF, JPEG and PNG files are accepted (extension + magic bytes agree),
- file size is capped (see settings.SOIL_REPORT_MAX_SIZE_MB),
- filenames are sanitised (basename only, restricted character set),
- the stored name is opaque (uuid); internal filesystem paths are never
  returned through the API.
"""

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.config import settings

# extension -> (mime type, magic-byte check)
ALLOWED_TYPES: dict[str, tuple[str, bytes]] = {
    ".pdf": ("application/pdf", b"%PDF-"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
}

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._\-\u00C0-\u024F ]+")


class SoilStorageError(ValueError):
    pass


@dataclass
class StoredReport:
    original_filename: str
    stored_filename: str
    content_type: str
    file_size_bytes: int


def sanitize_filename(name: str) -> str:
    """Keep only the basename and a safe character subset."""
    base = Path(name or "").name
    base = _SAFE_NAME_RE.sub("", base).strip(" .")
    if not base:
        raise SoilStorageError("The uploaded file has an unusable name")
    return base[:255]


def sniff_mime(head: bytes) -> Optional[tuple[str, bytes]]:
    """Return (mime, extension bytes) matching the magic bytes, or None."""
    for ext, (mime, magic) in ALLOWED_TYPES.items():
        if head.startswith(magic):
            return mime, magic
    return None


def validate_upload(filename: str, content_type: str, head: bytes, size: int) -> tuple[str, str]:
    """Validate filename extension, magic bytes and size.

    Returns (mime_type, extension). Raises SoilStorageError on rejection.
    """
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_TYPES:
        raise SoilStorageError(
            "Unsupported file type. Upload a PDF, JPEG or PNG of your soil report."
        )
    expected_mime, _magic = ALLOWED_TYPES[ext]
    sniffed = sniff_mime(head)
    if sniffed is None or sniffed[0] != expected_mime:
        raise SoilStorageError(
            "The file content does not match its extension. Upload an unmodified "
            "PDF, JPEG or PNG."
        )
    declared = (content_type or "").split(";")[0].strip().lower()
    # Be permissive about "application/octet-stream" from mobile browsers, but
    # reject a declared type that clearly contradicts the sniffed content.
    if declared and declared != "application/octet-stream" and declared not in (
        expected_mime,
        "application/octet-stream",
    ):
        raise SoilStorageError("The declared file type does not match its contents.")
    if size > settings.SOIL_REPORT_MAX_SIZE_BYTES:
        max_mb = settings.SOIL_REPORT_MAX_SIZE_MB
        raise SoilStorageError(f"File is too large. Maximum size is {max_mb} MB.")
    return expected_mime, ext


async def store_report(upload, original_filename: str, content_type: str) -> StoredReport:
    """Read an UploadFile, validate it, and write it under an opaque name."""
    head = await upload.read(4096)
    rest = await upload.read()
    payload = head + rest
    size = len(payload)

    expected_mime, ext = validate_upload(original_filename, content_type, payload, size)

    storage_dir = Path(settings.SOIL_REPORT_STORAGE_DIR)
    storage_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}{ext}"
    target = storage_dir / stored_name
    target.write_bytes(payload)

    safe_original = sanitize_filename(original_filename)
    return StoredReport(
        original_filename=safe_original,
        stored_filename=stored_name,
        content_type=expected_mime,
        file_size_bytes=size,
    )


def report_path(stored_filename: str) -> Path:
    """Resolve an opaque stored name to a real path without exposing it."""
    safe = Path(stored_filename).name
    return Path(settings.SOIL_REPORT_STORAGE_DIR) / safe