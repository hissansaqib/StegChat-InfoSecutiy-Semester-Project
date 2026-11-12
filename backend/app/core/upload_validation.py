"""Upload validation helper for StegChat media containers.

Responsibilities:
- File size caps from environment (MAX_UPLOAD_BYTES, MAX_IMAGE_PIXELS)
- Magic-byte sniffing for true content identification (PNG, WAV, UTF-8 text)
- Sanitized filenames & UUID-based internal storage paths
- PIL.Image decompression bomb protection (Image.MAX_IMAGE_PIXELS)
"""

from __future__ import annotations

import os
import re
import uuid
from typing import Tuple
from PIL import Image

# Enforce Pillow decompression bomb limit
MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", 25_000_000))
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 50 * 1024 * 1024))  # 50MB default

# Magic byte signatures
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
RIFF_MAGIC = b"RIFF"
WAVE_MAGIC = b"WAVE"

def sanitize_filename(filename: str) -> str:
    """Sanitize user-provided filename preventing path traversal or special chars."""
    basename = os.path.basename(filename)
    # Strip dangerous characters
    cleaned = re.sub(r"[^\w\.\- ]", "_", basename)
    return cleaned or f"file_{uuid.uuid4().hex[:8]}"

def generate_storage_name(extension: str = "") -> str:
    """Generate secure UUID-based storage filename."""
    ext = extension.lstrip(".")
    if ext:
        return f"{uuid.uuid4().hex}.{ext}"
    return uuid.uuid4().hex

def sniff_mime_type(data: bytes) -> str:
    """Sniff MIME type from raw file magic bytes."""
    if len(data) >= 8 and data[:8] == PNG_MAGIC:
        return "image/png"
    if len(data) >= 12 and data[:4] == RIFF_MAGIC and data[8:12] == WAVE_MAGIC:
        return "audio/wav"

    # Check for valid UTF-8 text
    try:
        data.decode("utf-8")
        return "text/plain"
    except UnicodeDecodeError:
        pass

    return "application/octet-stream"

def validate_upload(
    data: bytes,
    filename: str,
    allowed_mimes: list[str] | None = None,
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> Tuple[str, str, str]:
    """Validate uploaded bytes against size, magic sniffing, and format rules.
    
    Returns:
        (sanitized_filename, storage_name, detected_mime)
    Raises:
        ValueError: if file exceeds size, wrong format, or decompression bomb
    """
    if len(data) == 0:
        raise ValueError("Uploaded file is empty.")

    if len(data) > max_bytes:
        raise ValueError(f"File size {len(data)} exceeds maximum allowed {max_bytes} bytes.")

    detected_mime = sniff_mime_type(data)

    if allowed_mimes and detected_mime not in allowed_mimes:
        raise ValueError(
            f"Detected MIME type '{detected_mime}' is not permitted (allowed: {allowed_mimes})."
        )

    # Extra Pillow decompression bomb verification for PNG
    if detected_mime == "image/png":
        import io
        try:
            with Image.open(io.BytesIO(data)) as img:
                img.verify()
                if (img.width * img.height) > MAX_IMAGE_PIXELS:
                    raise ValueError(
                        f"Image pixel count ({img.width * img.height}) exceeds safety limit ({MAX_IMAGE_PIXELS})."
                    )
        except Exception as e:
            raise ValueError(f"Corrupt or unsafe PNG image: {e}")

    safe_name = sanitize_filename(filename)
    ext = os.path.splitext(safe_name)[1]
    storage_name = generate_storage_name(ext)

    return safe_name, storage_name, detected_mime
