from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConsentGive(BaseModel):
    purpose: str  # screening | storage | share_clinician | research
    consent_text: str | None = None
    version: str | None = None


class ConsentWithdraw(BaseModel):
    purpose: str
    reason: str | None = None


class ConsentOut(BaseModel):
    consent_id: str
    purpose: str
    status: str
    consent_text_version: str
    recorded_at: str
    is_active: bool
    withdrawn_at: str | None = None
