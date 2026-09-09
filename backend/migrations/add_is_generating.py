"""Add is_generating column to conversations table."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text
from app.core.database import engine


def migrate():
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE conversations "
            "ADD COLUMN IF NOT EXISTS is_generating BOOLEAN NOT NULL DEFAULT FALSE"
        ))
    print("Migration complete: is_generating column added to conversations table.")


if __name__ == "__main__":
    migrate()
