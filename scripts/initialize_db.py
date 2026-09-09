"""Initialize the database schema.

Creates all tables defined in backend/app/models using the configured database
(see MHC_DATABASE_URL in .env). Uses SQLAlchemy's metadata.create_all so it works
for both PostgreSQL and the SQLite used in tests.

Usage:
    python scripts/initialize_db.py            # create tables
    python scripts/initialize_db.py --sql      # also run database/schema.sql (Postgres)
"""
from __future__ import annotations

import argparse
import os
import sys

# Ensure the backend package is importable when run as a script.
BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, BACKEND)

from app.core.database import Base, engine  # noqa: E402
import app.models  # noqa: E402  (registers all models on Base.metadata)
from sqlalchemy import text  # noqa: E402


def create_all() -> None:
    Base.metadata.create_all(engine)
    print("Created tables:", sorted(Base.metadata.tables.keys()))


def run_sql_file(path: str) -> None:
    if not os.path.exists(path):
        print(f"SQL schema not found: {path}")
        return
    with engine.begin() as conn:
        conn.execute(text(open(path, encoding="utf-8").read()))
    print(f"Applied SQL schema from {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the database schema")
    parser.add_argument(
        "--sql", action="store_true",
        help="Also execute database/schema.sql (PostgreSQL).",
    )
    args = parser.parse_args()

    create_all()
    if args.sql:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        run_sql_file(os.path.join(repo_root, "database", "schema.sql"))


if __name__ == "__main__":
    main()
