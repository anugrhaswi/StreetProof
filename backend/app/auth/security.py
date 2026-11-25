import hashlib
import hmac
import secrets
import time
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from passlib.context import CryptContext

from app.config import settings

_pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

SESSION_COOKIE_NAME = "streetproof_admin_session"
CSRF_COOKIE_NAME = "streetproof_csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
SESSION_SALT = "admin-session"
CSRF_SALT = "admin-csrf"


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def _serializer(salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt=salt)


def create_session_token(username: str) -> str:
    payload = {
        "sub": username,
        "nonce": secrets.token_urlsafe(16),
        "iat": int(time.time()),
    }
    return _serializer(SESSION_SALT).dumps(payload)


def verify_session_token(token: str) -> dict[str, Any] | None:
    max_age = settings.admin_session_expire_minutes * 60
    try:
        data = _serializer(SESSION_SALT).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(data, dict) or data.get("sub") != settings.admin_username:
        return None
    return data


def create_csrf_token() -> str:
    # Signed token with random nonce; validated by signature and tied to session cookie via double-submit.
    payload = {"nonce": secrets.token_urlsafe(16), "iat": int(time.time())}
    return _serializer(CSRF_SALT).dumps(payload)


def verify_csrf_token(token: str) -> bool:
    max_age = settings.admin_session_expire_minutes * 60
    try:
        data = _serializer(CSRF_SALT).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return False
    return isinstance(data, dict) and "nonce" in data


def csrf_tokens_match(cookie_token: str | None, header_token: str | None) -> bool:
    if not cookie_token or not header_token:
        return False
    if not verify_csrf_token(cookie_token) or not verify_csrf_token(header_token):
        return False
    return hmac.compare_digest(cookie_token, header_token)


def get_admin_password_hash() -> str:
    # Hash the configured admin password on demand; avoid storing plaintext outside config.
    # For a single admin from env, hashing at check keeps config simple.
    return hash_password(settings.admin_password)


def timing_safe_username_match(username: str) -> bool:
    expected = settings.admin_username.encode("utf-8")
    provided = username.encode("utf-8")
    return hmac.compare_digest(
        hashlib.sha256(expected).digest(), hashlib.sha256(provided).digest()
    )
