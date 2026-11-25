from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import is_postgresql_database_url, is_sqlite_database_url, settings


def build_engine(database_url: str = settings.database_url):
    connect_args: dict[str, object] = {}
    engine_kwargs: dict[str, object] = {"future": True}

    if is_sqlite_database_url(database_url):
        connect_args = {"check_same_thread": False}
    elif is_postgresql_database_url(database_url):
        engine_kwargs.update(
            {
                "pool_pre_ping": bool(settings.database_pool_pre_ping),
                "pool_size": max(1, int(settings.database_pool_size)),
                "max_overflow": max(0, int(settings.database_max_overflow)),
                "pool_timeout": max(1, int(settings.database_pool_timeout_seconds)),
                "pool_recycle": max(0, int(settings.database_pool_recycle_seconds)),
            }
        )

    return create_engine(database_url, connect_args=connect_args, **engine_kwargs)


engine = build_engine()


if is_sqlite_database_url(settings.database_url):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
