"""Image fingerprinting for duplicate detection: SHA-256 and perceptual hash (pHash).

All functions are deterministic and safe on corrupt/invalid input.
"""

from __future__ import annotations

import hashlib
import logging
from io import BytesIO

import imagehash
from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

MAX_IMAGE_DIMENSION = 4096


def compute_sha256(content: bytes) -> str:
    """Return hex SHA-256 digest of raw bytes."""
    return hashlib.sha256(content).hexdigest()


def _normalize_image(img: Image.Image) -> Image.Image:
    """Normalize orientation (EXIF) and color mode for stable hashing."""
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    return img


def compute_phash(image_bytes: bytes, hash_size: int = 8) -> str | None:
    """Compute perceptual hash (pHash) as hex string. Returns None on invalid image."""
    if not image_bytes:
        return None
    try:
        with Image.open(BytesIO(image_bytes)) as img:
            img = _normalize_image(img)
            # Guard against decompression bombs / absurd dimensions.
            if img.width > MAX_IMAGE_DIMENSION or img.height > MAX_IMAGE_DIMENSION:
                img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
            ph = imagehash.phash(img, hash_size=hash_size)
            return str(ph)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        logger.warning("Failed to compute pHash: %s", exc)
        return None
    except Exception:
        logger.exception("Unexpected error computing pHash")
        return None


def hamming_distance(hash_hex_a: str, hash_hex_b: str) -> int | None:
    """Hamming distance between two hex pHash strings. None if incompatible."""
    if not hash_hex_a or not hash_hex_b:
        return None
    try:
        a = imagehash.hex_to_hash(hash_hex_a)
        b = imagehash.hex_to_hash(hash_hex_b)
        if a.hash.size != b.hash.size:
            return None
        return int(a - b)
    except Exception:
        logger.warning("Failed to compute hamming distance", exc_info=True)
        return None


def phash_similarity(hash_hex_a: str, hash_hex_b: str) -> float | None:
    """Normalized pHash similarity in [0,1]: 1 - (hamming / bit_count)."""
    dist = hamming_distance(hash_hex_a, hash_hex_b)
    if dist is None:
        return None
    try:
        a = imagehash.hex_to_hash(hash_hex_a)
        bit_count = int(a.hash.size)
        if bit_count <= 0:
            return None
        sim = 1.0 - (dist / bit_count)
        return max(0.0, min(1.0, float(sim)))
    except Exception:
        logger.warning("Failed to compute pHash similarity", exc_info=True)
        return None
