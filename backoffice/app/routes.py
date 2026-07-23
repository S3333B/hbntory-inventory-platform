"""Minimal protected routes used to verify authorization."""

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from backoffice.app.authentication import LogoutForm
from backoffice.app.authorization import admin_required, own_branch_required

main_blueprint = Blueprint("main", __name__)


@main_blueprint.get("/")
def index() -> str:
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@main_blueprint.get("/dashboard")
@login_required
def dashboard() -> str:
    return render_template(
        "dashboard.html",
        title="Dashboard",
        message="Authentication is active.",
        logout_form=LogoutForm(),
    )


@main_blueprint.get("/admin/users")
@admin_required
def user_management_authorization_probe() -> str:
    return render_template(
        "dashboard.html",
        title="User management",
        message="Administrator authorization granted.",
        logout_form=LogoutForm(),
    )


@main_blueprint.get("/stock/branches/<int:branch_id>")
@own_branch_required
def branch_stock_authorization_probe(branch_id: int) -> str:
    return render_template(
        "dashboard.html",
        title="Branch stock",
        message=f"Stock authorization granted for branch {branch_id}.",
        logout_form=LogoutForm(),
    )
