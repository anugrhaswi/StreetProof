from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from itsdangerous import URLSafeTimedSerializer

from app.auth.dependencies import login_rate_limiter
from app.auth.router import router as admin_auth_router
from app.auth.security import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME


def _csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get(CSRF_COOKIE_NAME)
    return {"X-CSRF-Token": token} if token else {}


class _FakeDB:
    def execute(self, *_args, **_kwargs):
        return SimpleNamespace(scalar=lambda: 0, scalars=lambda: SimpleNamespace(all=lambda: []))

    def scalar(self, *_args, **_kwargs):
        return 0


def _protected_app():
    from app.api.admin_dashboard import router as admin_dashboard_router
    from app.database import get_db

    app = FastAPI()
    app.include_router(admin_auth_router)
    app.include_router(admin_dashboard_router)

    def _override_db():
        yield _FakeDB()

    app.dependency_overrides[get_db] = _override_db
    return app


def _session_serializer(secret: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret, salt="admin-session")


def test_valid_login_sets_session_and_csrf_cookies(client: TestClient):
    res = client.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
    assert res.status_code == 200
    body = res.json()
    assert body["authenticated"] is True
    assert body["username"] == "admin"
    assert SESSION_COOKIE_NAME in client.cookies
    assert CSRF_COOKIE_NAME in client.cookies


def test_invalid_credentials_rejected(client: TestClient):
    res = client.post("/api/admin/login", json={"username": "admin", "password": "wrong"})
    assert res.status_code == 401
    assert SESSION_COOKIE_NAME not in client.cookies


def test_unauthenticated_cannot_access_protected_endpoint(app):
    # Build app with admin dashboard router included
    protected_app = _protected_app()
    with TestClient(protected_app) as c:
        res = c.get("/api/admin/dashboard/stats")
        assert res.status_code == 401


def test_authenticated_can_access_protected_endpoint():
    protected_app = _protected_app()
    with TestClient(protected_app) as c:
        login = c.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
        assert login.status_code == 200
        # endpoint may fail on db internals in this minimal app; 401 is the failure we're guarding against
        res = c.get("/api/admin/dashboard/stats")
        assert res.status_code != 401


def test_expired_session_rejected(monkeypatch):
    import app.auth.security as security

    protected_app = _protected_app()
    with TestClient(protected_app) as c:
        login = c.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
        assert login.status_code == 200
        real_datetime = security.datetime if hasattr(security, "datetime") else None
        # simulate expiry by patching max_age behavior through settings
        from app.config import settings

        old = settings.admin_session_expire_minutes
        settings.admin_session_expire_minutes = -1
        try:
            res = c.get("/api/admin/dashboard/stats")
            assert res.status_code == 401
        finally:
            settings.admin_session_expire_minutes = old
            if real_datetime is not None:
                monkeypatch.setattr(security, "datetime", real_datetime, raising=False)


def test_login_then_session_verification_succeeds(client: TestClient):
    login = client.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
    assert login.status_code == 200
    session = client.get("/api/admin/session")
    assert session.status_code == 200
    assert session.json() == {"authenticated": True, "username": "admin"}


def test_logout_invalidates_session():
    protected_app = _protected_app()
    with TestClient(protected_app) as c:
        login = c.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
        assert login.status_code == 200
        logout = c.post("/api/admin/logout", headers=_csrf_headers(c))
        assert logout.status_code == 204
        # session cookie should be cleared or invalid
        res = c.get("/api/admin/dashboard/stats")
        assert res.status_code == 401


def test_logout_clears_cookie_attributes_in_production(monkeypatch):
    import app.auth.router as auth_router
    from app.config import settings as app_settings

    old = {
        "environment": app_settings.environment,
        "debug": app_settings.debug,
        "secret_key": app_settings.secret_key,
        "admin_username": app_settings.admin_username,
        "admin_password": app_settings.admin_password,
        "cors_origins": app_settings.cors_origins,
        "admin_cookie_samesite": app_settings.admin_cookie_samesite,
    }
    monkeypatch.setattr(app_settings, "environment", "production")
    monkeypatch.setattr(app_settings, "debug", False)
    monkeypatch.setattr(app_settings, "secret_key", "prod-secret-key-with-at-least-32-characters")
    monkeypatch.setattr(app_settings, "admin_username", "prod-admin")
    monkeypatch.setattr(app_settings, "admin_password", "very-strong-prod-password")
    monkeypatch.setattr(app_settings, "cors_origins", ["https://street-proof.vercel.app"])
    monkeypatch.setattr(app_settings, "admin_cookie_samesite", None)
    auth_router._CONFIGURED_PASSWORD_HASH = None

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.normalized_cors_origins(),
        allow_origin_regex=app_settings.cors_origin_regex(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(admin_auth_router)
    try:
        with TestClient(app, base_url="https://api.streetproof.test") as c:
            login = c.post("/api/admin/login", json={"username": "prod-admin", "password": "very-strong-prod-password"})
            assert login.status_code == 200
            logout = c.post("/api/admin/logout", headers=_csrf_headers(c))
            assert logout.status_code == 204
            cleared = logout.headers.get_list("set-cookie")
            assert any(h.lower().startswith("streetproof_admin_session=") for h in cleared)
            assert any(h.lower().startswith("streetproof_csrf_token=") for h in cleared)
            for header in cleared:
                lower = header.lower()
                if "streetproof_admin_session=" in lower or "streetproof_csrf_token=" in lower:
                    assert "samesite=none" in lower
                    assert "secure" in lower
                    assert "path=/" in lower
    finally:
        for key, value in old.items():
            monkeypatch.setattr(app_settings, key, value)
        auth_router._CONFIGURED_PASSWORD_HASH = None


def test_csrf_protection_blocks_state_change_without_token():
    from app.api.admin_incidents import router as admin_incidents_router
    from app.database import get_db

    protected_app = FastAPI()
    protected_app.include_router(admin_auth_router)
    protected_app.include_router(admin_incidents_router)

    def _override_db():
        yield _FakeDB()

    protected_app.dependency_overrides[get_db] = _override_db
    with TestClient(protected_app) as c:
        login = c.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
        assert login.status_code == 200
        # no CSRF header
        res = c.patch("/api/admin/incidents/some-id/status", json={"status": "closed"})
        assert res.status_code == 403
        # wrong CSRF
        res = c.patch(
            "/api/admin/incidents/some-id/status",
            json={"status": "closed"},
            headers={"X-CSRF-Token": "bad-token"},
        )
        assert res.status_code == 403
        # correct CSRF (request may 404 because id not found, but should pass CSRF/auth)
        res = c.patch(
            "/api/admin/incidents/some-id/status",
            json={"status": "closed"},
            headers=_csrf_headers(c),
        )
        assert res.status_code in (200, 404)


def test_session_status_endpoint(client: TestClient):
    # anonymous
    res = client.get("/api/admin/session")
    assert res.status_code == 200
    assert res.json()["authenticated"] is False

    # logged in
    login = client.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
    assert login.status_code == 200
    res = client.get("/api/admin/session")
    assert res.status_code == 200
    body = res.json()
    assert body["authenticated"] is True
    assert body["username"] == "admin"


def test_login_rate_limiting(client: TestClient, monkeypatch):
    # shrink rate limit for test
    from app.config import settings

    monkeypatch.setattr(settings, "admin_login_rate_limit", 2)
    monkeypatch.setattr(settings, "admin_login_rate_window_seconds", 60)
    login_rate_limiter.reset()
    try:
        for _ in range(2):
            res = client.post("/api/admin/login", json={"username": "admin", "password": "wrong"})
            assert res.status_code == 401
        res = client.post("/api/admin/login", json={"username": "admin", "password": "wrong"})
        assert res.status_code == 429
    finally:
        login_rate_limiter.reset()
