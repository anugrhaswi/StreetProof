import io

from PIL import Image

from app.services.image_fingerprint import compute_phash, compute_sha256, hamming_distance, phash_similarity


def _make_image_bytes(color=(255, 0, 0), size=(64, 64), fmt="PNG") -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_sha256_generation_and_duplicate_detection():
    a = _make_image_bytes(color=(10, 20, 30))
    b = _make_image_bytes(color=(10, 20, 30))
    c = _make_image_bytes(color=(200, 10, 10))
    ha = compute_sha256(a)
    hb = compute_sha256(b)
    hc = compute_sha256(c)
    assert ha == hb
    assert ha != hc
    assert len(ha) == 64


def test_phash_generation_identical_and_similar_images():
    a = _make_image_bytes(color=(120, 120, 120), size=(128, 128))
    b = _make_image_bytes(color=(120, 120, 120), size=(64, 64))  # same content, different size
    pa = compute_phash(a, hash_size=8)
    pb = compute_phash(b, hash_size=8)
    assert pa is not None and pb is not None
    assert hamming_distance(pa, pb) == 0
    assert phash_similarity(pa, pb) == 1.0


def test_phash_different_images_lower_similarity():
    a = _make_image_bytes(color=(255, 255, 255), size=(64, 64))
    # Create a different pattern
    img = Image.new("RGB", (64, 64), color=(0, 0, 0))
    for x in range(0, 64, 2):
        for y in range(64):
            img.putpixel((x, y), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b = buf.getvalue()
    pa = compute_phash(a, hash_size=8)
    pb = compute_phash(b, hash_size=8)
    assert pa is not None and pb is not None
    sim = phash_similarity(pa, pb)
    assert sim is not None
    assert sim < 0.95


def test_phash_handles_formats_and_modes():
    img = Image.new("RGBA", (64, 64), color=(10, 20, 30, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    ph = compute_phash(buf.getvalue(), hash_size=8)
    assert ph is not None
    assert len(ph) > 0


def test_phash_corrupt_and_missing_images():
    assert compute_phash(b"not-an-image", hash_size=8) is None
    assert compute_phash(b"", hash_size=8) is None
    assert hamming_distance("", "abc") is None
    assert phash_similarity(None, "abc") is None  # type: ignore[arg-type]


def test_hamming_distance_values():
    a = "f" * 16
    b = "0" * 16
    dist = hamming_distance(a, b)
    assert dist == 64
    sim = phash_similarity(a, b)
    assert sim == 0.0
