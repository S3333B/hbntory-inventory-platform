"""Create the initial Backoffice schema without inserting data."""

import os

from backoffice.app.database import create_engine_from_url, create_schema


def main() -> None:
    """Create missing tables from SQLAlchemy metadata."""

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required to create the schema.")
    engine = create_engine_from_url(database_url)
    create_schema(engine)
    print("Backoffice schema created or already present.")


if __name__ == "__main__":
    main()
