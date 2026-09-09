"""C-SSRS / SAFE-T scoring logic.

The SAFE-T protocol is categorical (clinician-rated), not numeric.
Scoring is based on:
  - C-SSRS Ideation Severity (items 1-5): determines ideation level
  - C-SSRS Behavior: lifetime and recent
  - Risk/Protective factors: checklist counts
  - Clinician risk level determination: High / Moderate / Low

Safety rules:
  - C-SSRS ideation items 4 or 5 (intent/plan) -> HIGH RISK
  - Any suicidal behavior -> HIGH RISK
  - Ideation items 1-3 -> MODERATE RISK (requires further评估)
"""
from __future__ import annotations

from dataclasses import dataclass, field

IDEATION_ITEMS = [f"SAFE-T_SI_{i}" for i in range(1, 6)]
BEHAVIOR_ITEM = "SAFE-T_SB"

RISK_FACTOR_GROUPS = {
    "activating": "SAFE-T_RISK_ACTIVATING",
    "treatment": "SAFE-T_RISK_TREATMENT",
    "clinical": "SAFE-T_RISK_CLINICAL",
}
PROTECTIVE_FACTOR_GROUPS = {
    "internal": "SAFE-T_PROTECT_INTERNAL",
    "external": "SAFE-T_PROTECT_EXTERNAL",
}

INTENSITY_ITEMS = [
    "SAFE-T_INT_FREQUENCY",
    "SAFE-T_INT_DURATION",
    "SAFE-T_INT_CONTROLLABILITY",
    "SAFE-T_INT_DETERRENTS",
    "SAFE-T_INT_REASONS",
]


@dataclass
class CSSRSResult:
    ideation_level: int  # 0 = none, 1-5 = severity level
    has_ideation: bool
    has_intent: bool
    has_plan: bool
    has_behavior: bool
    behavior_recent: bool
    risk_factors_count: int
    protective_factors_count: int
    intensity_scores: dict[str, int]
    clinician_risk_level: str | None
    high_risk: bool
    interpretation: str


def score(
    responses: dict[str, str | list[str]],
    clinician_risk_level: str | None = None,
) -> CSSRSResult:
    """Score a completed SAFE-T / C-SSRS assessment.

    Args:
        responses: mapping of question_id -> response.
            - Ideation items (SI_1 to SI_5): "yes" or "no"
            - Behavior item (SB): "yes" or "no"
            - Risk/protective factors: list of checked items
            - Intensity items: option id string
        clinician_risk_level: Optional clinician-determined risk level
            ("high", "moderate", "low").

    Returns:
        CSSRSResult with ideation level, risk flags, and interpretation.
    """
    # Ideation severity: highest "yes" item (1-5)
    ideation_level = 0
    for i, item_id in enumerate(IDEATION_ITEMS, start=1):
        if responses.get(item_id) == "yes":
            ideation_level = i

    has_ideation = ideation_level > 0
    has_intent = ideation_level >= 4
    has_plan = ideation_level >= 5

    # Behavior
    has_behavior = responses.get(BEHAVIOR_ITEM) == "yes"
    # For simplicity, if behavior is "yes", we flag as recent unless explicitly "no"
    behavior_recent = has_behavior

    # Risk factors count
    risk_count = 0
    for group_key, group_id in RISK_FACTOR_GROUPS.items():
        items = responses.get(group_id, [])
        if isinstance(items, list):
            risk_count += len(items)

    # Protective factors count
    protective_count = 0
    for group_key, group_id in PROTECTIVE_FACTOR_GROUPS.items():
        items = responses.get(group_id, [])
        if isinstance(items, list):
            protective_count += len(items)

    # Intensity scores
    intensity = {}
    for item_id in INTENSITY_ITEMS:
        val = responses.get(item_id)
        if val and isinstance(val, str):
            # Extract numeric code from option id (e.g., "freq_3" -> 3)
            parts = val.split("_")
            if parts[-1].isdigit():
                intensity[item_id] = int(parts[-1])

    # High risk determination
    high_risk = has_intent or has_plan or has_behavior

    # Interpretation
    if has_plan:
        interpretation = "High risk: suicidal ideation with plan and/or intent"
    elif has_intent:
        interpretation = "High risk: suicidal ideation with intent"
    elif has_behavior:
        interpretation = "High risk: history of suicidal behavior"
    elif ideation_level == 3:
        interpretation = "Moderate risk: suicidal thoughts with method"
    elif ideation_level == 2:
        interpretation = "Moderate risk: active suicidal thoughts"
    elif ideation_level == 1:
        interpretation = "Low-moderate risk: passive ideation (wish to be dead)"
    else:
        interpretation = "No current suicidal ideation"

    return CSSRSResult(
        ideation_level=ideation_level,
        has_ideation=has_ideation,
        has_intent=has_intent,
        has_plan=has_plan,
        has_behavior=has_behavior,
        behavior_recent=behavior_recent,
        risk_factors_count=risk_count,
        protective_factors_count=protective_count,
        intensity_scores=intensity,
        clinician_risk_level=clinician_risk_level,
        high_risk=high_risk,
        interpretation=interpretation,
    )
