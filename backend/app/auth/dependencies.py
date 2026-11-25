import threading
import time
from collections import defaultdict, deque

from fastapi import Cookie, Header, HTTPException, Request, status

from app.auth.security import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
    csrf_tokens_match,
    verify_session_token,
)
from app.config import settings


class LoginRateLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        window = settings.admin_login_rate_window_seconds
        limit = settings.admin_login_rate_limit
        with self._lock:
            q = self._attempts[key]
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many login attempts. Please try again later.",
                )
            q.append(now)

    def reset(self) -> None:
        with self._lock:
            self._attempts.clear()


login_rate_limiter = LoginRateLimiter()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def get_current_admin(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, str]:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    data = verify_session_token(session_token)
    if not data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalid or expired")
    return {"username": str(data["sub"])}


def require_csrf(
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE_NAME),
    csrf_header: str | None = Header(default=None, alias=CSRF_HEADER_NAME),
) -> None:
    if not csrf_tokens_match(csrf_cookie, csrf_header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")
