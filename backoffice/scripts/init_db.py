"""Create and seed the initial Backoffice database."""

import os

from backoffice.app.database import create_engine_from_url
from backoffice.app.seed import INITIAL_EXTERNAL_PRODUCT_ID, initialize_database
from backoffice.app.services.product_validation import KnownProductValidator


def main() -> None:
    """Initialize deterministic data without logging any password."""

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required to initialize the database.")
    admin_password = os.environ.get("INITIAL_ADMIN_PASSWORD")
    if not admin_password:
        raise SystemExit(
            "INITIAL_ADMIN_PASSWORD is required and must not be empty."
        )

    engine = create_engine_from_url(database_url)
    validator = KnownProductValidator({INITIAL_EXTERNAL_PRODUCT_ID})
    result = initialize_database(
        engine,
        admin_password=admin_password,
        product_validator=validator,
    )
    print(
        "Backoffice database initialized: "
        f"admin_id={result.admin_id}, branches={len(result.branch_ids)}, "
        f"stocks={len(result.stock_ids)}."
    )


if __name__ == "__main__":
    main()
