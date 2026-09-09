"""PHQ-9 scoring logic.

Score range: 0-27 (sum of 9 items, each 0-3).
Severity bands (clinically verified):
  0-4:   Minimal depression
  5-9:   Mild depression
  10-14: Moderate depression
  15-19: Moderately severe depression
  20-27: Severe depression

Item 9 (PHQ9_09) is safety-relevant: any score >= 1 triggers safety workflow.
"""
from __future__ import annotations

from dataclasses import dataclass

ITEM_IDS = [f"PHQ9_{i:02d}" for i in range(1, 10)]
SAFETY_ITEM_ID = "PHQ9_09"

SEVERITY_BANDS = [
    (0, 4, "Minimal depression"),
    (5, 9, "Mild depression"),
    (10, 14, "Moderate depression"),
    (15, 19, "Moderately severe depression"),
    (20, 27, "Severe depression"),
]


@dataclass
class PHQ9Result:
    score: int
    interpretation: str
    high_risk: bool
    safety_flag: bool
    item_9_score: int


def score(responses: dict[str, int]) -> PHQ9Result:
    """Score a completed PHQ-9.

    Args:
        responses: mapping of question_id -> response score (0-3).

    Returns:
        PHQ9Result with total score, severity interpretation, and safety flags.
    """
    total = sum(responses.get(qid, 0) for qid in ITEM_IDS)
    total = max(0, min(27, total))

    interpretation = "Unknown"
    for low, high, label in SEVERITY_BANDS:
        if low <= total <= high:
            interpretation = label
            break

    item_9_score = responses.get(SAFETY_ITEM_ID, 0)
    safety_flag = item_9_score >= 1
    high_risk = safety_flag

    return PHQ9Result(
        score=total,
        interpretation=interpretation,
        high_risk=high_risk,
        safety_flag=safety_flag,
        item_9_score=item_9_score,
    )
