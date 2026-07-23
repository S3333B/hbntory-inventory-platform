"""Reusable backend authorization decorators."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar, cast

from flask import abort
from flask_login import current_user, login_required

from backoffice.app.models import UserRole

ViewFunction = TypeVar("ViewFunction", bound=Callable[..., Any])


def admin_required(view: ViewFunction) -> ViewFunction:
    """Allow only authenticated administrators."""

    @login_required
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if current_user.role != UserRole.ADMIN.value:
            abort(403)
        return view(*args, **kwargs)

    return cast(ViewFunction, wrapped)


def common_required(view: ViewFunction) -> ViewFunction:
    """Allow only authenticated common users."""

    @login_required
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if current_user.role != UserRole.COMMON.value:
            abort(403)
        return view(*args, **kwargs)

    return cast(ViewFunction, wrapped)


def own_branch_required(view: ViewFunction) -> ViewFunction:
    """Restrict a common user to the branch_id present in the route."""

    @login_required
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        branch_id = kwargs.get("branch_id")
        if (
            current_user.role != UserRole.COMMON.value
            or current_user.branch_id != branch_id
        ):
            abort(403)
        return view(*args, **kwargs)

    return cast(ViewFunction, wrapped)
