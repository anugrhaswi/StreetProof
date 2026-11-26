from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_client_ip, get_current_admin, login_rate_limiter, require_csrf
from app.auth.security import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    create_csrf_token,
    create_session_token,
    hash_password,
    timing_safe_username_match,
    verify_password,
    verify_session_token,
)
from app.config import settings

router = APIRouter(prefix="/api/admin", tags=["admin"])

_CONFIGURED_PASSWORD_HASH: str | None = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=256)


class AdminStatusResponse(BaseModel):
    authenticated: bool
    username: str | None = None


class LoginResponse(BaseModel):
    authenticated: bool
    username: str


def _configured_password_hash() -> str:
    global _CONFIGURED_PASSWORD_HASH
    if _CONFIGURED_PASSWORD_HASH is None:
        _CONFIGURED_PASSWORD_HASH = hash_password(settings.admin_password)
    return _CONFIGURED_PASSWORD_HASH


def _cookie_secure() -> bool:
    # Secure=true in production (HTTPS). Local development/test over HTTP keep Secure=false.
    return settings.cookie_secure()


def _cookie_samesite() -> str:
    # Production defaults to SameSite=None for cross-site Vercel->Render admin auth.
    # Development/test default to Lax for local HTTP workflows.
    return settings.cookie_samesite()


def _cookie_params() -> dict[str, object]:
    return {
        "secure": _cookie_secure(),
        "samesite": _cookie_samesite(),
        "path": "/",
    }


def _set_auth_cookies(response: Response, username: str) -> None:
    max_age = settings.admin_session_expire_minutes * 60
    cookie_params = _cookie_params()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(username),
        max_age=max_age,
        httponly=True,
        **cookie_params,
    )
    # Double-submit CSRF cookie is JS-readable; header must match on state-changing requests.
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=create_csrf_token(),
        max_age=max_age,
        httponly=False,
        **cookie_params,
    )


def _clear_auth_cookies(response: Response) -> None:
    cookie_params = _cookie_params()
    response.delete_cookie(key=SESSION_COOKIE_NAME, **cookie_params)
    response.delete_cookie(key=CSRF_COOKIE_NAME, **cookie_params)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response) -> LoginResponse:
    login_rate_limiter.check(get_client_ip(request))

    username_ok = timing_safe_username_match(payload.username)
    password_ok = verify_password(payload.password, _configured_password_hash())
    if not username_ok or not password_ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    _set_auth_cookies(response, settings.admin_username)
    return LoginResponse(authenticated=True, username=settings.admin_username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    _admin: dict[str, str] = Depends(get_current_admin),
    _csrf: None = Depends(require_csrf),
) -> Response:
    _clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/session", response_model=AdminStatusResponse)
def session_status(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> AdminStatusResponse:
    if not session_token:
        return AdminStatusResponse(authenticated=False)
    data = verify_session_token(session_token)
    if not data:
        return AdminStatusResponse(authenticated=False)
    return AdminStatusResponse(authenticated=True, username=str(data.get("sub")))
