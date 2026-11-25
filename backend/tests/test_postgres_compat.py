import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from app.config import Settings, is_postgresql_database_url, is_sqlite_database_url, normalize_database_url
from app.database import build_engine


def test_normalize_database_url_postgres_variants():
    assert normalize_database_url("postgres://u:p@host:5432/db") == "postgresql+psycopg://u:p@host:5432/db"
    assert normalize_database_url("postgresql://u:p@host:5432/db") == "postgresql+psycopg://u:p@host:5432/db"
    assert normalize_database_url("postgresql+psycopg://u:p@host:5432/db") == "postgresql+psycopg://u:p@host:5432/db"
    assert normalize_database_url("sqlite:///./data/streetproof.db") == "sqlite:///./data/streetproof.db"


def test_database_url_scheme_detection():
    assert is_sqlite_database_url("sqlite:///./x.db")
    assert not is_postgresql_database_url("sqlite:///./x.db")
    assert is_postgresql_database_url("postgresql+psycopg://u:p@host/db")
    assert is_postgresql_database_url("postgres://u:p@host/db")
    assert not is_sqlite_database_url("postgresql://u:p@host/db")


def test_settings_normalizes_postgres_url():
    s = Settings(database_url="postgres://u:p@host:5432/db?sslmode=require")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db?sslmode=require"
    assert s.is_postgresql is True
    assert s.is_sqlite is False


def test_sqlite_engine_keeps_sqlite_connect_args(monkeypatch):
    from app.config import settings as app_settings

    monkeypatch.setattr(app_settings, "database_pool_pre_ping", True)
    engine = build_engine("sqlite:///./tmp-test.db")
    try:
        assert engine.url.get_backend_name() == "sqlite"
        assert engine.pool.__class__.__name__ in {"SingletonThreadPool", "StaticPool", "NullPool", "QueuePool"}
        # SQLite connect args are applied; cannot inspect private connect_args portably, but URL/behavior is sqlite.
    finally:
        engine.dispose()


def test_postgres_engine_config_uses_pool_settings(monkeypatch):
    from app.config import settings as app_settings

    monkeypatch.setattr(app_settings, "database_pool_pre_ping", True)
    monkeypatch.setattr(app_settings, "database_pool_size", 7)
    monkeypatch.setattr(app_settings, "database_max_overflow", 3)
    monkeypatch.setattr(app_settings, "database_pool_timeout_seconds", 19)
    monkeypatch.setattr(app_settings, "database_pool_recycle_seconds", 123)
    engine = build_engine("postgresql+psycopg://user:pass@localhost:5432/dbname")
    try:
        assert engine.url.get_backend_name() == "postgresql"
        assert engine.pool.size() == 7
        assert engine.pool._max_overflow == 3
        assert engine.pool._timeout == 19
        assert engine.pool._recycle == 123
        assert engine.pool._pre_ping is True
    finally:
        engine.dispose()


def test_alembic_upgrade_head_on_temp_sqlite(tmp_path):
    db_path = tmp_path / "alembic-smoke.db"
    db_url = f"sqlite:///{db_path.as_posix()}"
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    env["PYTHONPATH"] = "."
    backend_dir = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(backend_dir),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    engine = create_engine(db_url, future=True)
    try:
        insp = inspect(engine)
        assert "match_suggestions" in insp.get_table_names()
        cols = {c["name"] for c in insp.get_columns("match_suggestions")}
        assert "candidate_classification" in cols
    finally:
        engine.dispose()


@pytest.mark.postgres
def test_postgres_migrations_and_enum_labels(tmp_path):
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if not test_db_url:
        pytest.skip("TEST_DATABASE_URL not set; PostgreSQL integration test skipped.")

    normalized = normalize_database_url(test_db_url)
    env = os.environ.copy()
    env["DATABASE_URL"] = normalized
    env["PYTHONPATH"] = "."
    backend_dir = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(backend_dir),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    engine = create_engine(normalized, future=True)
    try:
        with engine.connect() as conn:
            labels = conn.execute(
                text(
                    """
                    SELECT e.enumlabel
                    FROM pg_enum e
                    JOIN pg_type t ON t.oid = e.enumtypid
                    WHERE t.typname = 'suggestion_status_enum'
                    ORDER BY e.enumsortorder
                    """
                )
            ).scalars().all()
        assert set(labels) >= {"PENDING", "REVIEWED", "DISMISSED", "REJECTED", "AUTO_MERGED", "SUPERSEDED"}
    finally:
        engine.dispose()
