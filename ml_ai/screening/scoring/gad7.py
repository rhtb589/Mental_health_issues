"""GAD-7 scoring logic.

Score range: 0-21 (sum of 7 items, each 0-3).
Severity bands:
  0-4:  Minimal anxiety
  5-9:  Mild anxiety
  10-14: Moderate anxiety
  15-21: Severe anxiety
"""
from __future__ import annotations

from dataclasses import dataclass

ITEM_IDS = [f"GAD7_{i:02d}" for i in range(1, 8)]

SEVERITY_BANDS = [
    (0, 4, "Minimal anxiety"),
    (5, 9, "Mild anxiety"),
    (10, 14, "Moderate anxiety"),
    (15, 21, "Severe anxiety"),
]


@dataclass
class GAD7Result:
    score: int
    interpretation: str
    high_risk: bool


def score(responses: dict[str, int]) -> GAD7Result:
    """Score a completed GAD-7.

    Args:
        responses: mapping of question_id -> response score (0-3).

    Returns:
        GAD7Result with total score and severity interpretation.
    """
    total = sum(responses.get(qid, 0) for qid in ITEM_IDS)
    total = max(0, min(21, total))

    interpretation = "Unknown"
    for low, high, label in SEVERITY_BANDS:
        if low <= total <= high:
            interpretation = label
            break

    return GAD7Result(
        score=total,
        interpretation=interpretation,
        high_risk=False,
    )
