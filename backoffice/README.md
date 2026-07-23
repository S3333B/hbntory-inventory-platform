# HBntory Backoffice

Task 1 provides the SQLAlchemy models, database constraints, stock business
rules, deterministic initialization, and database tests. Task 2 adds the Flask
application foundation, session authentication, and reusable backend
authorization. Complete stock and user-management interfaces remain later work.

## Technology

- Python 3.10 or newer;
- SQLAlchemy 2.x directly, without Flask-SQLAlchemy;
- PostgreSQL with Psycopg 3;
- Werkzeug PBKDF2 password hashing;
- Flask with Jinja server-side rendering;
- Flask-Login session authentication;
- Flask-WTF CSRF protection;
- pytest with SQLite for network-free unit tests.

Dependency versions are pinned in `backoffice/requirements.txt`.

## Structure

```text
backoffice/
├── app/
│   ├── __init__.py             # Flask app factory and SQLAlchemy integration
│   ├── authentication.py       # Login, logout, and password verification
│   ├── authorization.py        # Role and branch decorators
│   ├── config.py               # Environment-backed secure configuration
│   ├── database.py             # Engine, sessions, and create_all bootstrap
│   ├── models/                 # User, Branch, and Stock
│   ├── routes.py               # Minimal protected authorization probes
│   ├── services/               # Product validation and stock rules
│   ├── templates/              # Minimal authentication templates
│   └── seed.py                 # Idempotent initial data
├── scripts/
│   ├── create_schema.py
│   └── init_db.py
├── tests/
└── requirements.txt
```

## Authentication strategy

The Backoffice uses server-rendered Flask pages and signed session cookies, so
Flask-Login is used instead of JWT authentication. The browser session stores
only Flask-Login's user identifier and CSRF state. Passwords, password hashes,
roles, branch identifiers, and the secret key are not copied into the cookie.

Every protected request reloads the user from PostgreSQL. A missing or
soft-deleted user is treated as anonymous, which revokes access from a user
deleted after login. Anonymous users are redirected to `/login`; authenticated
users without the required permission receive HTTP `403`.

Login performs these steps:

1. Flask-WTF validates the form and CSRF token.
2. SQLAlchemy looks up the exact username.
3. Werkzeug verifies the submitted password against the stored PBKDF2 hash.
4. Unknown, deleted, and invalid-password cases return the same public message.
5. The previous session is cleared before Flask-Login creates the authenticated
   session.
6. A `next` destination is used only when it is a local absolute path.

Logout is a CSRF-protected `POST /logout`. It calls Flask-Login logout and clears
the remaining session state.

## Password security

`User.set_password()` creates hashes with `pbkdf2:sha256:600000` and a random
16-byte salt. `authentication.verify_password()` uses Werkzeug's verification
helper; the original password cannot be recovered from the hash.

PBKDF2 deliberately repeats the hash operation many times, making password
guessing more expensive. The random salt prevents identical passwords from
having identical stored hashes and defeats precomputed rainbow tables. Plain
SHA256 alone is designed to be fast and therefore is not suitable for password
storage.

Passwords, hashes, `SECRET_KEY`, and session cookies are never logged.

## Authorization

Authorization is enforced by reusable backend decorators:

| Rule | Admin | Common |
| --- | --- | --- |
| Authenticated dashboard | Allowed | Allowed |
| User management | Allowed | HTTP `403` |
| Stock operation | HTTP `403` | Own branch only |
| Another branch through a modified URL/ID | HTTP `403` | HTTP `403` |

The current placeholder routes exist only to verify these controls:

- `GET /dashboard` — any authenticated user;
- `GET /admin/users` — administrator only;
- `GET /stock/branches/<branch_id>` — common user for their own branch only.

They do not implement the complete Task 3 stock or user-management interfaces.

## Configuration

| Variable | Requirement |
| --- | --- |
| `DATABASE_URL` | Required for the SQLAlchemy engine. |
| `SECRET_KEY` | Required outside tests; use a long random local value. |
| `SESSION_COOKIE_SECURE` | `false` for local HTTP; `true` behind HTTPS. |

Session cookies are always `HttpOnly` and use `SameSite=Lax`. TLS is not required
by the development subject, but HTTPS and `SESSION_COOKIE_SECURE=true` are
mandatory for a production deployment.

Automated tests inject an isolated SQLite URL and test-only configuration.
There is no production secret fallback.

## Install dependencies

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backoffice/requirements.txt
```

## Local PostgreSQL

Copy `.env.example` to an ignored `.env`, replace every placeholder password,
and start PostgreSQL:

```bash
docker compose up -d postgres
docker compose ps
```

The current scripts run from the host, so `DATABASE_URL` uses `localhost` and
`POSTGRES_HOST_PORT`.

## Create the schema

```bash
python -m backoffice.scripts.create_schema
```

This calls `Base.metadata.create_all()`. It is suitable only for initial schema
creation. It does not replace versioned migrations and will not update existing
columns or constraints.

## Initialize data

Set a real local password in the environment before running:

```bash
export INITIAL_ADMIN_PASSWORD='<strong-local-password>'
python -m backoffice.scripts.init_db
```

The command fails if `DATABASE_URL` or `INITIAL_ADMIN_PASSWORD` is missing. It
never logs the password. It creates the `admin` user, Lille and Roubaix, and
stock for official external product `1`. Re-running it does not create
duplicates.

The initializer uses an offline allow-list for the already validated seed
product. A real `ProductValidator` HTTP implementation will be added during
Backoffice/Product API integration and will continue to store only the numeric
identifier.

## Start the Backoffice

After creating and initializing the database:

```bash
export DATABASE_URL='postgresql+psycopg://hbntory:<local-password>@localhost:5432/hbntory'
export SECRET_KEY='<long-random-local-secret>'
export SESSION_COOKIE_SECURE=false
flask --app backoffice.app:create_app run --debug
```

Open `http://127.0.0.1:5000/login`. The initial username is `admin`; its password
is the local value previously supplied through `INITIAL_ADMIN_PASSWORD`. No
default password is stored in the repository.

## Run tests

```bash
python -m pytest backoffice/tests
```

Tests use isolated SQLite databases and an injectable fake product validator.
They do not contact production PostgreSQL or the External Product API.
Authentication tests exercise CSRF, generic login failures, session creation
and logout, soft-delete revocation, safe redirects, role enforcement, and
branch ownership.

## Data rules

- common users belong to exactly one branch;
- administrators have no branch assignment;
- usernames and case-insensitive branch names are unique;
- user deletion sets `deleted_at` instead of deleting the row;
- stock is unique per `(branch_id, external_product_id)` and cannot be negative;
- branch foreign keys use restricted deletion;
- product metadata is never stored locally.

## Current limits

- no complete stock-management pages;
- no complete administrator user-management pages;
- no Product API display integration;
- no password reset, public registration, OAuth, or JWT;
- no Backoffice Docker service yet;
- `Base.metadata.create_all()` remains an initial bootstrap, not a migration
  system.
