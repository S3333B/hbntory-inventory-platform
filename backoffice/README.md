# Backoffice Service

The future Backoffice is the only service allowed to change local users, branches, and stock.

## Planned technology

- Python;
- Flask;
- Jinja server-side rendering;
- SQLAlchemy;
- PostgreSQL;
- Flask-Login sessions;
- Werkzeug PBKDF2 password hashing.

## Responsibilities

- authenticate internal users and manage sessions;
- enforce administrator and common-user permissions;
- manage branches and stock for authorized common users;
- allow administrators to manage users;
- retrieve product details from the external Product API for display;
- expose authenticated, read-only internal stock endpoints to MCP.

## Required rules

- every common user belongs to exactly one branch;
- common users manage stock only for their own branch and cannot manage users;
- administrators manage users but cannot manage stock;
- users are soft-deleted, and deleted users cannot sign in;
- stock never becomes negative;
- stock adjustments use positive integers;
- product metadata is not stored in PostgreSQL.

No Flask routes, SQLAlchemy models, authentication logic, or other application code is implemented during Task 0.
