import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.auth.router import router as admin_auth_router
from app.config import Settings, validate_runtime_settings


def _prod_settings(**overrides):
    base = dict(
        environment="production",
        debug=False,
        secret_key="prod-secret-key-with-at-least-32-characters",
        admin_username="prod-admin",
        admin_password="very-strong-prod-password",
        cors_origins=["https://streetproof.vercel.app"],
        storage_backend="supabase",
        supabase_url="https://example-project.supabase.co",
        supabase_service_role_key="service-role-test-key",
        supabase_storage_bucket="report-images",
    )
    base.update(overrides)
    return Settings(**base)


def test_production_startup_missing_secret_key_fails():
    settings = _prod_settings(secret_key="")
    with pytest.raises(RuntimeError) as exc:
        validate_runtime_settings(settings)
    msg = str(exc.value)
    assert "SECRET_KEY must be set in production" in msg
    assert "very-strong-prod-password" not in msg


def test_production_startup_default_admin_credentials_fail():
    settings = _prod_settings(admin_username="admin", admin_password="changeme")
    with pytest.raises(RuntimeError) as exc:
        validate_runtime_settings(settings)
    msg = str(exc.value)
    assert "ADMIN_USERNAME must not use the default value in production" in msg
    assert "ADMIN_PASSWORD must not use the default value in production" in msg
    assert "changeme" not in msg


def test_production_startup_debug_true_fails():
    settings = _prod_settings(debug=True)
    with pytest.raises(RuntimeError) as exc:
        validate_runtime_settings(settings)
    assert "DEBUG must be false in production" in str(exc.value)


def test_production_startup_missing_cors_origins_fails():
    settings = _prod_settings(cors_origins=[])
    with pytest.raises(RuntimeError) as exc:
        validate_runtime_settings(settings)
    assert "CORS_ORIGINS must be explicitly configured in production" in str(exc.value)


def test_production_rejects_wildcard_cors_with_credentials():
    settings = _prod_settings(cors_origins=["*"])
    with pytest.raises(RuntimeError) as exc:
        validate_runtime_settings(settings)
    assert "must not include '*'" in str(exc.value)


def test_development_configuration_still_works():
    settings = Settings(environment="development", debug=True)
    validate_runtime_settings(settings)
    assert settings.normalized_cors_origins() == ["http://localhost:5173", "http://127.0.0.1:5173"]
    assert settings.cors_origin_regex() is not None
    assert settings.cookie_secure() is False
    assert settings.cookie_samesite() == "lax"


def test_production_cookies_configured_securely(monkeypatch):
    import app.auth.router as auth_router
    import app.auth.security as auth_security
    from app.config import settings as app_settings

    old = {
        "environment": app_settings.environment,
        "debug": app_settings.debug,
        "secret_key": app_settings.secret_key,
        "admin_username": app_settings.admin_username,
        "admin_password": app_settings.admin_password,
        "cors_origins": app_settings.cors_origins,
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
        with TestClient(app, base_url="https://api.streetproof.test") as client:
            res = client.post("/api/admin/login", json={"username": "prod-admin", "password": "very-strong-prod-password"})
            assert res.status_code == 200
            set_cookie_headers = res.headers.get_list("set-cookie")
            assert any("streetproof_admin_session=" in h for h in set_cookie_headers)
            assert any("streetproof_csrf_token=" in h for h in set_cookie_headers)
            for header in set_cookie_headers:
                lower = header.lower()
                assert "secure" in lower
                assert "samesite=none" in lower
                assert "path=/" in lower
            session_header = next(h for h in set_cookie_headers if "streetproof_admin_session=" in h.lower())
            csrf_header = next(h for h in set_cookie_headers if "streetproof_csrf_token=" in h.lower())
            assert "httponly" in session_header.lower()
            assert "httponly" not in csrf_header.lower()
    finally:
        for key, value in old.items():
            monkeypatch.setattr(app_settings, key, value)
        auth_router._CONFIGURED_PASSWORD_HASH = None
        # ensure security serializer uses restored key for subsequent tests
        assert auth_security.settings is app_settings


def test_production_credentialed_cors_allows_configured_origin_only():
    from app.main import create_app
    settings = _prod_settings(cors_origins=["https://street-proof.vercel.app"])
    app = create_app(settings)
    with TestClient(app) as client:
        allowed = client.options(
            "/api/admin/session",
            headers={
                "Origin": "https://street-proof.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert allowed.status_code == 200
        assert allowed.headers.get("access-control-allow-origin") == "https://street-proof.vercel.app"
        assert allowed.headers.get("access-control-allow-credentials") == "true"

        denied = client.options(
            "/api/admin/session",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert denied.headers.get("access-control-allow-origin") != "https://evil.example"


def test_production_explicit_lax_override_still_supported(monkeypatch):
    settings = _prod_settings(admin_cookie_samesite="lax")
    validate_runtime_settings(settings)
    assert settings.cookie_samesite() == "lax"
    # Secure is still required in production
    assert settings.cookie_secure() is True
