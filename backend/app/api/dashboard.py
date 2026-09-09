"""Dashboard endpoints.

Provides aggregate statistics for the admin/dashboard view.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, Integer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.security.permissions import require_admin, Principal
from app.models.user import User
from app.models.assessment import Assessment
from app.models.consent import ConsentRecord
from app.models.assignment import Assignment

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats(
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total_users = db.execute(select(func.count()).select_from(User)).scalar_one()
    active_users = db.execute(
        select(func.count()).select_from(User).where(User.is_active.is_(True))
    ).scalar_one()
    total_assessments = db.execute(select(func.count()).select_from(Assessment)).scalar_one()
    completed_assessments = db.execute(
        select(func.count()).select_from(Assessment).where(Assessment.status == "completed")
    ).scalar_one()
    high_risk_count = db.execute(
        select(func.count()).select_from(Assessment).where(Assessment.high_risk.is_(True))
    ).scalar_one()

    # Consents
    total_consents = db.execute(select(func.count()).select_from(ConsentRecord)).scalar_one()
    active_consents = db.execute(
        select(func.count()).select_from(ConsentRecord).where(ConsentRecord.is_active.is_(True))
    ).scalar_one()

    # Assignments
    total_assignments = db.execute(
        select(func.count()).select_from(Assessment).where(Assessment.is_de_identified.is_(False))
    ).scalar_one()

    # By instrument
    by_instrument = (
        db.execute(
            select(
                Assessment.instrument_id,
                func.count().label("total"),
                func.sum(func.cast(Assessment.high_risk, Integer)).label("high_risk"),
            )
            .group_by(Assessment.instrument_id)
        )
        .mappings()
        .all()
    )

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_assessments": total_assessments,
        "completed_assessments": completed_assessments,
        "high_risk_count": high_risk_count,
        "total_consents": total_consents,
        "active_consents": active_consents,
        "by_instrument": [
            {
                "instrument_id": r["instrument_id"],
                "total": r["total"],
                "high_risk": int(r["high_risk"] or 0),
            }
            for r in by_instrument
        ],
    }
