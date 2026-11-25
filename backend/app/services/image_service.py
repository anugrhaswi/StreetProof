import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.services.image_fingerprint import compute_phash, compute_sha256

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024


def ensure_upload_dir() -> Path:
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

    Returns (relative_path, sha256_hash, phash_hex, phash_size).
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
        from io import BytesIO

        with Image.open(BytesIO(content)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is not a valid image.")

    sha256_hash = compute_sha256(content)
    phash_size = int(settings.phash_hash_size)
    phash_hex = compute_phash(content, hash_size=phash_size)
    if not phash_hex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to compute image fingerprint.")

    upload_dir = ensure_upload_dir()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    destination = upload_dir / unique_name
    with destination.open("wb") as out_file:
        out_file.write(content)

    relative_path = f"uploads/{unique_name}"
    return relative_path, sha256_hash, phash_hex, phash_size
