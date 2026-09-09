"""Database session and declarative base.

PostgreSQL is used as the system of record (see database/schema.sql). This module
provides the SQLAlchemy engine, session factory and a FastAPI dependency.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# Server-side parameter binding with pooled connections.
connect_args = (
    {"options": "-c timezone=UTC"} if settings.database_url.startswith("postgresql") else {}
)

engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
