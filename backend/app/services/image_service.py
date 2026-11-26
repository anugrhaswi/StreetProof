import uuid
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.services.image_fingerprint import compute_phash, compute_sha256
from app.services.storage import StorageUploadResult, get_storage_service

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024


def ensure_upload_dir() -> Path:
    """Ensure local upload dir exists (used by local storage and legacy static mount)."""
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _validate_extension(filename: str | None) -> str:
    if not filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image filename is required.")
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only JPG, JPEG, and PNG are allowed.",
        )
    return ".jpg" if ext == ".jpeg" else ext


async def save_image(file: UploadFile) -> tuple[str, str, str, int]:
    """Validate, persist, and fingerprint an uploaded image.

    Returns (image_path, sha256_hash, phash_hex, phash_size).
    image_path is a stable storage reference: legacy/local "uploads/<file>" or
    a full public Supabase Storage URL in production.
    """
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image MIME type. Only image/jpeg and image/png are allowed.",
        )

    ext = _validate_extension(file.filename)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded image is empty.")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image exceeds the 5 MB size limit.",
        )

    # Verify it's a real image before persisting.
    try:
        with Image.open(BytesIO(content)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is not a valid image.")

    sha256_hash = compute_sha256(content)
    phash_size = int(settings.phash_hash_size)
    phash_hex = compute_phash(content, hash_size=phash_size)
    if not phash_hex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to compute image fingerprint.")

    unique_name = f"{uuid.uuid4().hex}{ext}"
    storage = get_storage_service(settings)
    result: StorageUploadResult = storage.upload_bytes(
        content=content,
        filename=unique_name,
        content_type=file.content_type or "application/octet-stream",
    )
    return result.image_path, sha256_hash, phash_hex, phash_size


def delete_image(image_path: str | None) -> bool:
    """Delete an image from the configured storage backend. Returns True when deleted."""
    storage = get_storage_service(settings)
    return storage.delete(image_path)


def read_image_bytes(image_path: str | None) -> bytes | None:
    """Read image bytes from the configured storage backend/local legacy path."""
    if not image_path:
        return None
    storage = get_storage_service(settings)
    return storage.read_bytes(image_path)
