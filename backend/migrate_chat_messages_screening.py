"""Add suggested_instrument and suggested_at columns to chat_messages."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text
from app.core.database import engine


def upgrade():
    with engine.begin() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE chat_messages ADD COLUMN suggested_instrument VARCHAR(50) NULL"
            ))
            print("Added column: chat_messages.suggested_instrument")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("Column chat_messages.suggested_instrument already exists, skipping")
            else:
                raise

        try:
            conn.execute(text(
                "ALTER TABLE chat_messages ADD COLUMN suggested_at TIMESTAMP WITH TIME ZONE NULL"
            ))
            print("Added column: chat_messages.suggested_at")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("Column chat_messages.suggested_at already exists, skipping")
            else:
                raise

    print("Migration complete.")


def downgrade():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE chat_messages DROP COLUMN IF EXISTS suggested_at"))
        conn.execute(text("ALTER TABLE chat_messages DROP COLUMN IF EXISTS suggested_instrument"))
    print("Rollback complete.")


if __name__ == "__main__":
    upgrade()
