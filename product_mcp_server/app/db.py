"""Database configuration helpers for the Product MCP Server stock tools.

Reuses Backoffice engine/session helpers so the same SQLAlchemy models and
URL conventions apply. The MCP process never starts the Flask application.
"""

from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backoffice.app.database import create_engine_from_url, make_session_factory


def create_stock_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Build a SQLAlchemy engine for stock reads (PostgreSQL or SQLite tests)."""

    return create_engine_from_url(database_url, echo=echo)


def create_stock_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a session factory bound to the stock engine."""

    return make_session_factory(engine)
