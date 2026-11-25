from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_admin, require_csrf
from app.auth.security import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME, create_session_token


def _csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get(CSRF_COOKIE_NAME)
    return {"X-CSRF-Token": token} if token else {}


def _add_protected_route(app: FastAPI) -> None:
    @app.get("/api/admin/protected-test")
    def protected_test(_admin: dict = Depends(get_current_admin)):
        return {"ok": True, "username": _admin["username"]}

    @app.post("/api/admin/protected-write", dependencies=[Depends(get_current_admin), Depends(require_csrf)])
    def protected_write():
        return {"ok": True}


def test_valid_login_sets_session_and_csrf_cookies(client: TestClient):
    res = client.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
    assert res.status_code == 200
    body = res.json()
    assert body["authenticated"] is True
    assert body["username"] == "admin"
    assert SESSION_COOKIE_NAME in res.cookies
    assert CSRF_COOKIE_NAME in res.cookies


def test_invalid_credentials_rejected(client: TestClient):
    res = client.post("/api/admin/login", json={"username": "admin", "password": "wrong"})
    assert res.status_code == 401
    assert "Invalid credentials" in res.json()["detail"]
    assert SESSION_COOKIE_NAME not in res.cookies


def test_unauthenticated_cannot_access_protected_endpoint(app: FastAPI):
    _add_protected_route(app)
    with TestClient(app) as c:
        res = c.get("/api/admin/protected-test")
    assert res.status_code == 401


def test_authenticated_can_access_protected_endpoint(app: FastAPI):
    _add_protected_route(app)
    with TestClient(app) as c:
        login = c.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
        assert login.status_code == 200
        res = c.get("/api/admin/protected-test")
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["username"] == "admin"


def test_expired_session_rejected(app: FastAPI, monkeypatch):
    _add_protected_route(app)
    import time as time_mod
    from app.config import settings

    monkeypatch.setattr(settings, "admin_session_expire_minutes", 1)
    real_time = time_mod.time()
    with TestClient(app) as c:
        token = create_session_token("admin")
        c.cookies.set(SESSION_COOKIE_NAME, token)
        monkeypatch.setattr(time_mod, "time", lambda: real_time + 120)
        monkeypatch.setattr("itsdangerous.timed.time.time", lambda: real_time + 120, raising=False)
        res = c.get("/api/admin/protected-test")
    assert res.status_code == 401


def test_logout_invalidates_session(app: FastAPI):
    _add_protected_route(app)
    with TestClient(app) as c:
        login = c.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
        assert login.status_code == 200

        logout = c.post("/api/admin/logout", headers=_csrf_headers(c))
        assert logout.status_code == 204

        # Session cookie should be cleared/invalid for protected endpoint
        res = c.get("/api/admin/protected-test")
        assert res.status_code == 401


def test_csrf_protection_blocks_state_change_without_token(app: FastAPI):
    _add_protected_route(app)
    with TestClient(app) as c:
        login = c.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
        assert login.status_code == 200

        # Missing CSRF header
        res = c.post("/api/admin/protected-write")
        assert res.status_code == 403

        # Wrong CSRF header
        res = c.post("/api/admin/protected-write", headers={"X-CSRF-Token": "bad-token"})
        assert res.status_code == 403

        # Correct CSRF header
        res = c.post("/api/admin/protected-write", headers=_csrf_headers(c))
        assert res.status_code == 200


def test_session_status_endpoint(client: TestClient):
    # Unauthenticated
    res = client.get("/api/admin/session")
    assert res.status_code == 200
    assert res.json() == {"authenticated": False, "username": None}

    # Authenticated
    login = client.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
    assert login.status_code == 200
    res = client.get("/api/admin/session")
    assert res.status_code == 200
    assert res.json()["authenticated"] is True
    assert res.json()["username"] == "admin"


def test_login_rate_limiting(client: TestClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "admin_login_rate_limit", 2)
    monkeypatch.setattr(settings, "admin_login_rate_window_seconds", 60)

    for _ in range(2):
        res = client.post("/api/admin/login", json={"username": "admin", "password": "wrong"})
        assert res.status_code == 401

    res = client.post("/api/admin/login", json={"username": "admin", "password": "wrong"})
    assert res.status_code == 429
