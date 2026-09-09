"""Researcher endpoints (RBAC: anonymized / aggregated data only).

Requirement (RBAC): Researchers may access only anonymized / aggregated data.
These endpoints deliberately never return identifiable records, scores, or
answers, and expose only cohort-level aggregates computed over de-identified
assessments.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, Integer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.security.permissions import require_role, Principal
from app.security.authorization import Role
from app.models.assessment import Assessment

router = APIRouter(prefix="/research", tags=["research"])


@router.get("/aggregates/by-instrument")
def aggregate_by_instrument(
    principal: Principal = Depends(require_role(Role.RESEARCHER)),
    db: Session = Depends(get_db),
):
    rows = (
        db.execute(
            select(
                Assessment.instrument_id,
                func.count().label("total"),
                func.sum(func.cast(Assessment.high_risk, Integer)).label("high_risk"),
            )
            .where(Assessment.is_de_identified.is_(True))
            .group_by(Assessment.instrument_id)
        )
        .mappings()
        .all()
    )
    return [
        {
            "instrument_id": r["instrument_id"],
            "assessments": r["total"],
            "high_risk": int(r["high_risk"] or 0),
        }
        for r in rows
    ]


@router.get("/aggregates/high-risk-rate")
def high_risk_rate(
    principal: Principal = Depends(require_role(Role.RESEARCHER)),
    db: Session = Depends(get_db),
):
    total = db.execute(
        select(func.count()).select_from(Assessment).where(Assessment.is_de_identified.is_(True))
    ).scalar_one()
    high = db.execute(
        select(func.count())
        .select_from(Assessment)
        .where(Assessment.is_de_identified.is_(True), Assessment.high_risk.is_(True))
    ).scalar_one()
    return {
        "de_identified_assessments": total,
        "high_risk_assessments": high,
        "high_risk_rate": (high / total) if total else 0.0,
    }
