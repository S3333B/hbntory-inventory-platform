"""Flask application factory and database exports for the Backoffice."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backoffice.app.database import (
    create_engine_from_url,
    create_schema,
    make_session_factory,
)
from backoffice.app.models import Base, Branch, Stock, User, UserRole

if TYPE_CHECKING:
    from flask import Flask
    from sqlalchemy.orm import Session


def create_app(test_config: dict[str, object] | None = None) -> Flask:
    """Create a configured Backoffice application without import side effects.

    Flask-only imports intentionally stay inside the factory. This allows other
    internal services to reuse the SQLAlchemy models and database helpers
    without importing or starting the Flask application.
    """

    from flask import Flask, g, render_template
    from flask_wtf.csrf import CSRFError, CSRFProtect

    from backoffice.app.authentication import init_authentication
    from backoffice.app.config import build_config

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_mapping(build_config(test_config))

    engine = create_engine_from_url(app.config["DATABASE_URL"])
    session_factory = make_session_factory(engine)
    app.extensions["hbntory_engine"] = engine
    app.extensions["hbntory_session_factory"] = session_factory

    CSRFProtect(app)
    init_authentication(app)

    from backoffice.app.authentication import auth_blueprint
    from backoffice.app.routes import main_blueprint

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(main_blueprint)

    @app.teardown_appcontext
    def close_database_session(_exception: BaseException | None = None) -> None:
        database_session = g.pop("database_session", None)
        if database_session is not None:
            database_session.close()

    @app.errorhandler(403)
    def forbidden(_error: object) -> tuple[str, int]:
        return render_template("403.html"), 403

    @app.errorhandler(CSRFError)
    def csrf_error(_error: CSRFError) -> tuple[str, int]:
        return render_template("400.html"), 400

    return app


def get_database_session() -> Session:
    """Return one SQLAlchemy session scoped to the current Flask request."""

    from flask import current_app, g

    if "database_session" not in g:
        factory = current_app.extensions["hbntory_session_factory"]
        g.database_session = factory()
    return g.database_session


__all__ = [
    "Base",
    "Branch",
    "Stock",
    "User",
    "UserRole",
    "create_app",
    "create_engine_from_url",
    "create_schema",
    "get_database_session",
    "make_session_factory",
]
