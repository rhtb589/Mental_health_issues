"""Screening engine: orchestrate scoring and interpretation for all instruments.

Routes instrument_id to the appropriate scorer and returns a unified result.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ml_ai.screening.scoring import phq9, gad7, phq4, cssrs


INSTRUMENT_SCORERS = {
    "PHQ9": "phq9",
    "PHQ-9": "phq9",
    "GAD7": "gad7",
    "GAD-7": "gad7",
    "PHQ4": "phq4",
    "PHQ-4": "phq4",
    "SAFE-T": "safe_t",
    "SAFET": "safe_t",
    "C-SSRS": "safe_t",
}


@dataclass
class ScreeningResult:
    instrument_id: str
    score: Any
    interpretation: str
    high_risk: bool
    details: dict[str, Any]


def run_screening(
    instrument_id: str,
    responses: dict[str, Any],
    clinician_risk_level: str | None = None,
) -> ScreeningResult:
    """Run screening for the given instrument and responses.

    Args:
        instrument_id: The instrument identifier (e.g., "PHQ9", "GAD-7").
        responses: Mapping of question_id -> response value.
        clinician_risk_level: For SAFE-T only, the clinician's risk level.

    Returns:
        ScreeningResult with score, interpretation, and risk flags.

    Raises:
        ValueError: If instrument_id is not recognized.
    """
    normalized = instrument_id.upper().replace("-", "").replace(" ", "")
    scorer_key = INSTRUMENT_SCORERS.get(instrument_id.upper()) or INSTRUMENT_SCORERS.get(normalized)

    if scorer_key is None:
        raise ValueError(f"Unknown instrument: {instrument_id}")

    if scorer_key == "phq9":
        result = phq9.score(responses)
        return ScreeningResult(
            instrument_id="PHQ9",
            score=result.score,
            interpretation=result.interpretation,
            high_risk=result.high_risk,
            details={
                "safety_flag": result.safety_flag,
                "item_9_score": result.item_9_score,
                "severity": result.interpretation,
            },
        )

    if scorer_key == "gad7":
        result = gad7.score(responses)
        return ScreeningResult(
            instrument_id="GAD7",
            score=result.score,
            interpretation=result.interpretation,
            high_risk=result.high_risk,
            details={"severity": result.interpretation},
        )

    if scorer_key == "phq4":
        result = phq4.score(responses)
        return ScreeningResult(
            instrument_id="PHQ4",
            score=result.score,
            interpretation=result.interpretation,
            high_risk=result.high_risk,
            details={
                "anxiety_subscale": result.anxiety_subscale,
                "depression_subscale": result.depression_subscale,
                "severity": result.interpretation,
            },
        )

    if scorer_key == "safe_t":
        result = cssrs.score(responses, clinician_risk_level=clinician_risk_level)
        return ScreeningResult(
            instrument_id="SAFE-T",
            score={
                "ideation_level": result.ideation_level,
                "risk_factors": result.risk_factors_count,
                "protective_factors": result.protective_factors_count,
            },
            interpretation=result.interpretation,
            high_risk=result.high_risk,
            details={
                "has_ideation": result.has_ideation,
                "has_intent": result.has_intent,
                "has_plan": result.has_plan,
                "has_behavior": result.has_behavior,
                "clinician_risk_level": result.clinician_risk_level,
                "intensity_scores": result.intensity_scores,
            },
        )

    raise ValueError(f"No scorer implemented for: {instrument_id}")
