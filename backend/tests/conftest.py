"""Shared pytest fixtures.

Configures an isolated SQLite database and FastAPI test client for the
privacy/consent/retention/RBAC/audit test suites.
"""
from __future__ import annotations

import os
import tempfile

# --- Isolate the app from any real environment -------------------------------
_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["MHC_DATABASE_URL"] = f"sqlite:///{_db_file.name}"
os.environ["MHC_JWT_SECRET"] = "test-secret"
os.environ["MHC_FIELD_ENCRYPTION_KEY"] = "test-key-32-bytes-long-xxxxxxxxxx"
os.environ["MHC_IDENTIFIABLE_RETENTION_YEARS"] = "5"
os.environ["MHC_HIGH_RISK_RETENTION_YEARS"] = "7"
os.environ["MHC_AUDIT_LOG_RETENTION_YEARS"] = "3"
os.environ["MHC_INACTIVE_GRACE_DAYS"] = "365"
os.environ["MHC_DEFAULT_ROLE"] = "patient"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
import app.models  # noqa: E402  (register models)
from app.main import app  # noqa: E402
from app.core.database import get_db  # noqa: E402


def _seed_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


# Run once per session.
_seed_db()


import pytest  # noqa: E402


@pytest.fixture
def db() -> Session:
    """A fresh session per test; tables are reset by the client/db fixtures."""
    _seed_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db: Session) -> TestClient:
    """FastAPI test client bound to the test database session."""

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
