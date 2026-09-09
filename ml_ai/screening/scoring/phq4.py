"""PHQ-4 scoring logic.

Score range: 0-12 (sum of 4 items, each 0-3).
Severity bands:
  0-2:  Minimal
  3-5:  Mild
  6-8:  Moderate
  9-12: Severe

Items 1-2 assess anxiety; items 3-4 assess depression.
"""
from __future__ import annotations

from dataclasses import dataclass

ANXIETY_ITEMS = ["PHQ4_01", "PHQ4_02"]
DEPRESSION_ITEMS = ["PHQ4_03", "PHQ4_04"]
ALL_ITEMS = ANXIETY_ITEMS + DEPRESSION_ITEMS

SEVERITY_BANDS = [
    (0, 2, "Minimal"),
    (3, 5, "Mild"),
    (6, 8, "Moderate"),
    (9, 12, "Severe"),
]


@dataclass
class PHQ4Result:
    score: int
    interpretation: str
    anxiety_subscale: int
    depression_subscale: int
    high_risk: bool


def score(responses: dict[str, int]) -> PHQ4Result:
    """Score a completed PHQ-4.

    Args:
        responses: mapping of question_id -> response score (0-3).

    Returns:
        PHQ4Result with total score, subscale scores, and severity interpretation.
    """
    total = sum(responses.get(qid, 0) for qid in ALL_ITEMS)
    total = max(0, min(12, total))

    anxiety = sum(responses.get(qid, 0) for qid in ANXIETY_ITEMS)
    depression = sum(responses.get(qid, 0) for qid in DEPRESSION_ITEMS)

    interpretation = "Unknown"
    for low, high, label in SEVERITY_BANDS:
        if low <= total <= high:
            interpretation = label
            break

    return PHQ4Result(
        score=total,
        interpretation=interpretation,
        anxiety_subscale=anxiety,
        depression_subscale=depression,
        high_risk=False,
    )
