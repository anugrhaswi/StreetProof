from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol
from urllib.parse import quote, unquote, urlparse

import httpx
from fastapi import HTTPException, status

from app.config import Settings, settings

logger = logging.getLogger(__name__)

# Legacy/local stored paths: "uploads/<filename>" or "/uploads/<filename>".
LEGACY_UPLOADS_PREFIX = "uploads/"


def is_absolute_http_url(value: str | None) -> bool:
    if not isinstance(value, str):
        return False
    lower = value.strip().lower()
    return lower.startswith("http://") or lower.startswith("https://")


def normalize_legacy_upload_path(image_path: str | None) -> str | None:
    if not image_path:
        return None
    clean = image_path.strip().replace("\\", "/").lstrip("/")
    if not clean:
        return None
    if clean.startswith(LEGACY_UPLOADS_PREFIX):
        return clean
    # Bare filename fallback for legacy records.
    if "/" not in clean:
        return f"{LEGACY_UPLOADS_PREFIX}{clean}"
    return clean


def legacy_upload_filename(image_path: str | None) -> str | None:
    normalized = normalize_legacy_upload_path(image_path)
    if not normalized or not normalized.startswith(LEGACY_UPLOADS_PREFIX):
        return None
    name = Path(normalized).name
    if not name or name in {".", ".."}:
        return None
    return name


@dataclass(frozen=True)
class StorageUploadResult:
    image_path: str
    storage_key: str | None = None


class StorageService(Protocol):
    def upload_bytes(self, *, content: bytes, filename: str, content_type: str) -> StorageUploadResult: ...

    def read_bytes(self, image_path: str) -> bytes | None: ...

    def delete(self, image_path: str | None) -> bool: ...

    def public_url(self, image_path: str | None) -> str | None: ...


class LocalStorageService:
    def __init__(self, app_settings: Settings = settings):
        self._settings = app_settings

    @property
    def upload_dir(self) -> Path:
        path = Path(self._settings.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def upload_bytes(self, *, content: bytes, filename: str, content_type: str) -> StorageUploadResult:  # noqa: ARG002
        safe_name = Path(filename).name
        if not safe_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload filename.")
        destination = self.upload_dir / safe_name
        destination.write_bytes(content)
        relative_path = f"{LEGACY_UPLOADS_PREFIX}{safe_name}"
        return StorageUploadResult(image_path=relative_path, storage_key=relative_path)

    def read_bytes(self, image_path: str) -> bytes | None:
        # Local backend can also read absolute local/static URLs in dev tests if they map to /uploads/<file>.
        if is_absolute_http_url(image_path):
            parsed = urlparse(image_path)
            if parsed.path.startswith("/uploads/"):
                image_path = parsed.path.lstrip("/")
            else:
                return None
        filename = legacy_upload_filename(image_path)
        if not filename:
            return None
        target = (self.upload_dir / filename).resolve()
        upload_root = self.upload_dir.resolve()
        if not target.is_relative_to(upload_root):
            logger.warning("Blocked local image read outside upload dir")
            return None
        if not target.exists() or not target.is_file():
            return None
        try:
            return target.read_bytes()
        except Exception:
            logger.warning("Failed reading local image %s", filename, exc_info=True)
            return None

    def delete(self, image_path: str | None) -> bool:
        if not image_path:
            return False
        if is_absolute_http_url(image_path):
            # Local backend does not own remote URLs.
            return False
        filename = legacy_upload_filename(image_path)
        if not filename:
            return False
        try:
            upload_root = self.upload_dir.resolve()
            target = (upload_root / filename).resolve()
            if not target.is_relative_to(upload_root):
                logger.warning("Blocked local image deletion outside upload dir")
                return False
            if not target.exists():
                logger.warning("Local image file missing during delete: %s", filename)
                return False
            target.unlink()
            return True
        except Exception:
            logger.warning("Failed deleting local image %s", image_path, exc_info=True)
            return False

    def public_url(self, image_path: str | None) -> str | None:
        if not image_path:
            return None
        if is_absolute_http_url(image_path):
            return image_path.strip()
        normalized = normalize_legacy_upload_path(image_path)
        return f"/{normalized}" if normalized else None


class SupabaseStorageService:
    def __init__(self, app_settings: Settings = settings):
        self._settings = app_settings
        self._base_url = (app_settings.supabase_url or "").strip().rstrip("/")
        self._bucket = (app_settings.supabase_storage_bucket or "").strip()
        self._key = (app_settings.supabase_service_role_key or "").strip()
        if not self._base_url or not self._bucket or not self._key:
            raise RuntimeError("Supabase storage is not configured.")

    @property
    def bucket(self) -> str:
        return self._bucket

    def _headers(self, *, content_type: str | None = None, upsert: bool = False) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._key}",
            "apikey": self._key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        if upsert:
            headers["x-upsert"] = "true"
        return headers

    def _object_url(self, object_key: str) -> str:
        key = object_key.lstrip("/")
        encoded = quote(key, safe="/")
        return f"{self._base_url}/storage/v1/object/{quote(self._bucket, safe='')}/{encoded}"

    def public_object_url(self, object_key: str) -> str:
        key = object_key.lstrip("/")
        encoded = quote(key, safe="/")
        return f"{self._base_url}/storage/v1/object/public/{quote(self._bucket, safe='')}/{encoded}"

    def object_key_from_image_path(self, image_path: str | None) -> str | None:
        if not image_path or not is_absolute_http_url(image_path):
            return None
        parsed = urlparse(image_path.strip())
        base = urlparse(self._base_url)
        # Only extract keys for configured Supabase project URL.
        if parsed.netloc != base.netloc:
            return None
        path = unquote(parsed.path or "")
        prefixes = [
            f"/storage/v1/object/public/{self._bucket}/",
            f"/storage/v1/object/{self._bucket}/",
        ]
        for prefix in prefixes:
            if path.startswith(prefix):
                key = path[len(prefix):].lstrip("/")
                if not key:
                    return None
                # Normalize to safe posix key; prevent traversal.
                parts = [p for p in PurePosixPath(key).parts if p not in ("", ".", "..")]
                if not parts:
                    return None
                return "/".join(parts)
        return None

    def upload_bytes(self, *, content: bytes, filename: str, content_type: str) -> StorageUploadResult:
        safe_name = Path(filename).name
        if not safe_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload filename.")
        object_key = f"reports/{safe_name}"
        url = self._object_url(object_key)
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, content=content, headers=self._headers(content_type=content_type, upsert=False))
        except httpx.HTTPError:
            logger.exception("Supabase Storage upload request failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Image storage is temporarily unavailable. Please try again.",
            ) from None

        if resp.status_code not in (200, 201):
            logger.error("Supabase Storage upload failed with status %s", resp.status_code)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to store image. Please try again.",
            )

        return StorageUploadResult(image_path=self.public_object_url(object_key), storage_key=object_key)

    def read_bytes(self, image_path: str) -> bytes | None:
        if not image_path:
            return None
        # Preserve compatibility with legacy/local records.
        if not is_absolute_http_url(image_path):
            return LocalStorageService(self._settings).read_bytes(image_path)

        target_url = image_path.strip()
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(target_url)
                # If public URL fails but object belongs to configured bucket, retry with service-role auth.
                if resp.status_code >= 400:
                    object_key = self.object_key_from_image_path(image_path)
                    if object_key:
                        auth_resp = client.get(self._object_url(object_key), headers=self._headers())
                        resp = auth_resp
        except httpx.HTTPError:
            logger.warning("Supabase Storage read request failed for image", exc_info=True)
            return None

        if resp.status_code == 404:
            logger.warning("Supabase Storage object not found for configured image path")
            return None
        if resp.status_code >= 400:
            logger.warning("Supabase Storage read failed with status %s", resp.status_code)
            return None
        return resp.content

    def delete(self, image_path: str | None) -> bool:
        if not image_path:
            return False
        if not is_absolute_http_url(image_path):
            # Legacy local path - best effort local cleanup.
            return LocalStorageService(self._settings).delete(image_path)
        object_key = self.object_key_from_image_path(image_path)
        if not object_key:
            # Not a Supabase object for this project/bucket; do not attempt unsafe delete.
            return False
        url = self._object_url(object_key)
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.delete(url, headers=self._headers())
        except httpx.HTTPError:
            logger.warning("Supabase Storage delete request failed", exc_info=True)
            return False

        if resp.status_code in (200, 204):
            return True
        if resp.status_code == 404:
            logger.warning("Supabase Storage object missing during delete")
            return False
        logger.warning("Supabase Storage delete failed with status %s", resp.status_code)
        return False

    def public_url(self, image_path: str | None) -> str | None:
        if not image_path:
            return None
        if is_absolute_http_url(image_path):
            return image_path.strip()
        # If a raw key was stored accidentally, construct public URL.
        clean = image_path.strip().lstrip("/")
        if clean:
            return self.public_object_url(clean)
        return None


def get_storage_service(app_settings: Settings = settings) -> StorageService:
    backend = (app_settings.storage_backend or "local").strip().lower()
    if backend == "supabase":
        return SupabaseStorageService(app_settings)
    return LocalStorageService(app_settings)


def is_supabase_public_url(image_path: str | None, app_settings: Settings = settings) -> bool:
    if not image_path or not is_absolute_http_url(image_path):
        return False
    try:
        svc = SupabaseStorageService(app_settings)
    except Exception:
        return False
    return svc.object_key_from_image_path(image_path) is not None
