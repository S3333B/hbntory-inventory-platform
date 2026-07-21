"""Engine, session, and initial schema helpers."""

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backoffice.app.models import Base


def create_engine_from_url(database_url: str, *, echo: bool = False) -> Engine:
    """Build a SQLAlchemy engine for PostgreSQL or isolated SQLite tests."""

    if not isinstance(database_url, str) or not database_url.strip():
        raise ValueError("DATABASE_URL must be a non-empty string.")

    url = make_url(database_url)
    engine = create_engine(url, echo=echo, pool_pre_ping=True)

    if url.get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create the shared SQLAlchemy 2.x session factory."""

    return sessionmaker(bind=engine, expire_on_commit=False)


def create_schema(engine: Engine) -> None:
    """Create missing tables for the initial foundation schema.

    This bootstrap helper is intentionally not a long-term migration system.
    """

    Base.metadata.create_all(engine)
