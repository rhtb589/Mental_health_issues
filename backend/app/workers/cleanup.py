"""Retention / anonymization cleanup worker.

Runs the periodic retention sweep requirement:
  * anonymize users whose identifiable retention window has elapsed
  * anonymize high-risk assessments that exceeded their clinical retention
  * process pending data-subject deletion / anonymization requests

Run manually:  python -m app.workers.cleanup
Or schedule via cron / a task queue.
"""
from __future__ import annotations

import sys
import os

# Allow running as a script: ensure project root on path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal  # noqa: E402
from app.services import retention_service  # noqa: E402
from app.services import audit_service  # noqa: E402


def main() -> dict:
    db = SessionLocal()
    try:
        summary = retention_service.run_retention_sweep(db)
        db.commit()
        return summary
    finally:
        db.close()


if __name__ == "__main__":
    result = main()
    print("Retention sweep summary:", result)
