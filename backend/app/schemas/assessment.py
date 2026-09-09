from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AssessmentCreate(BaseModel):
    instrument_id: str
    instrument_version: str | None = None


class ResponseAdd(BaseModel):
    question_id: str
    response_value: Any


class AssessmentFinalize(BaseModel):
    score: Any
    interpretation: str
    high_risk: bool = False
    high_risk_detail: str | None = None


class AssessmentOut(BaseModel):
    assessment_id: str
    instrument_id: str
    instrument_version: str | None = None
    status: str
    high_risk: bool
    high_risk_detail: str | None = None
    is_de_identified: bool
    started_at: str
    completed_at: str | None = None
    # Decrypted score/interpretation are only returned to authorized viewers.
    score: Any | None = None
    interpretation: str | None = None


class AssignmentCreate(BaseModel):
    patient_id: str
    provider_id: str
    provider_role: str
