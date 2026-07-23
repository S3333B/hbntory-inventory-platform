"""Session authentication for internal Backoffice users."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from urllib.parse import urlsplit

from flask import (
    Blueprint,
    Flask,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf import FlaskForm
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import HiddenField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired

from backoffice.app.models import User

GENERIC_LOGIN_ERROR = "Invalid username or password."

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to access this page."

auth_blueprint = Blueprint("auth", __name__)


@dataclass(frozen=True)
class AuthenticatedUser(UserMixin):
    """Minimal, non-sensitive user data kept for the current request."""

    id: int
    username: str
    role: str
    branch_id: int | None

    def get_id(self) -> str:
        return str(self.id)


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    next_url = HiddenField()
    submit = SubmitField("Sign in")


class LogoutForm(FlaskForm):
    submit = SubmitField("Sign out")


def init_authentication(app: Flask) -> None:
    """Initialize Flask-Login and one ephemeral timing-defense hash."""

    login_manager.init_app(app)
    app.extensions["authentication_dummy_hash"] = generate_password_hash(
        secrets.token_urlsafe(32),
        method="pbkdf2:sha256:600000",
        salt_length=16,
    )


def verify_password(password_hash: str, candidate: str) -> bool:
    """Verify a candidate through Werkzeug without recovering the password."""

    if not isinstance(password_hash, str) or not isinstance(candidate, str):
        return False
    try:
        return check_password_hash(password_hash, candidate)
    except (TypeError, ValueError):
        return False


def _session_user(user: User) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=user.id,
        username=user.username,
        role=user.role,
        branch_id=user.branch_id,
    )


@login_manager.user_loader
def load_user(user_id: str) -> AuthenticatedUser | None:
    """Reload active users on every request so soft deletion revokes access."""

    try:
        numeric_id = int(user_id)
    except (TypeError, ValueError):
        return None

    from backoffice.app import get_database_session

    user = get_database_session().get(User, numeric_id)
    if user is None or user.is_deleted:
        return None
    return _session_user(user)


def safe_next_url(candidate: str | None) -> str | None:
    """Accept local absolute paths only, preventing open redirects."""

    if not candidate or not isinstance(candidate, str):
        return None
    parsed = urlsplit(candidate)
    if (
        parsed.scheme
        or parsed.netloc
        or not candidate.startswith("/")
        or candidate.startswith("//")
        or "\\" in candidate
    ):
        return None
    return candidate


@auth_blueprint.route("/login", methods=["GET", "POST"])
def login() -> str | tuple[str, int]:
    """Authenticate one active internal user with a generic failure response."""

    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if request.method == "GET":
        form.next_url.data = safe_next_url(request.args.get("next")) or ""

    if form.validate_on_submit():
        from backoffice.app import get_database_session

        username = form.username.data.strip()
        user = get_database_session().scalar(
            select(User).where(User.username == username)
        )
        password_hash = (
            user.password_hash
            if user is not None
            else current_app.extensions["authentication_dummy_hash"]
        )
        password_matches = verify_password(password_hash, form.password.data)

        if user is not None and not user.is_deleted and password_matches:
            destination = safe_next_url(form.next_url.data)
            authenticated_user = _session_user(user)
            session.clear()
            login_user(authenticated_user, remember=False, fresh=True)
            return redirect(destination or url_for("main.dashboard"))

    if request.method == "POST":
        flash(GENERIC_LOGIN_ERROR, "error")
        return render_template("login.html", form=form), 401
    return render_template("login.html", form=form)


@auth_blueprint.post("/logout")
@login_required
def logout() -> str:
    """End the authenticated session; CSRF is enforced globally."""

    if current_user.is_authenticated:
        logout_user()
    session.clear()
    return redirect(url_for("auth.login"))
