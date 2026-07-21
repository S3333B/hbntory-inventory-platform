# Backoffice Database Foundation

Task 1 provides the SQLAlchemy models, database constraints, stock business rules, deterministic initialization, and automated tests. It does not implement Flask routes, login sessions, HTML, or the administrator interface.

## Technology

- Python 3.10 or newer;
- SQLAlchemy 2.x directly, without Flask-SQLAlchemy;
- PostgreSQL with Psycopg 3;
- Werkzeug PBKDF2 password hashing;
- pytest with SQLite for network-free unit tests.

Dependency versions are pinned in `backoffice/requirements.txt`.

## Structure

```text
backoffice/
├── app/
│   ├── database.py              # Engine, sessions, and create_all bootstrap
│   ├── models/                  # User, Branch, and Stock
│   ├── services/                # Injectable product validation and stock rules
│   └── seed.py                  # Idempotent initial data
├── scripts/
│   ├── create_schema.py
│   └── init_db.py
├── tests/
└── requirements.txt
```

## Local PostgreSQL

Copy `.env.example` to an ignored `.env`, replace every placeholder password, and start PostgreSQL without changing the External Product API service:

```bash
docker compose up -d postgres
docker compose ps
```

The current scripts run from the host, so `DATABASE_URL` uses `localhost` and `POSTGRES_HOST_PORT`. A future Backoffice container will use the `postgres` Compose service name.

## Create the schema

```bash
python -m backoffice.scripts.create_schema
```

This calls `Base.metadata.create_all()`. It is suitable only for initial schema creation. It does not replace versioned migrations and will not update existing columns or constraints.

## Initialize data

Set a real local password in the environment before running:

```bash
export INITIAL_ADMIN_PASSWORD='<strong-local-password>'
python -m backoffice.scripts.init_db
```

The command fails if `DATABASE_URL` or `INITIAL_ADMIN_PASSWORD` is missing. It never logs the password. It creates the `admin` user, Lille and Roubaix, and stock for official external product `1`. Re-running it does not create duplicates.

The initializer uses an offline allow-list for the already validated seed product. A real `ProductValidator` HTTP implementation will be added during Backoffice/Product API integration and will continue to store only the numeric identifier.

## Run tests

```bash
python -m pytest backoffice/tests
```

Tests use an injectable fake product validator and do not contact PostgreSQL or the External Product API.

## Data rules

- common users belong to exactly one branch;
- administrators have no branch assignment;
- usernames and case-insensitive branch names are unique;
- user deletion sets `deleted_at` instead of deleting the row;
- stock is unique per `(branch_id, external_product_id)` and cannot be negative;
- branch foreign keys use restricted deletion;
- product names, SKU values, descriptions, prices, images, suppliers, categories, and metadata are never stored locally.
