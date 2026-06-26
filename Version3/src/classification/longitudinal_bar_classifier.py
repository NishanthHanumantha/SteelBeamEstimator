"""Phase D.4.1 — map longitudinal bar geometry to estimator categories."""

from typing import Literal, Optional, Tuple

Position = Literal["TOP", "BOTTOM", "UNKNOWN"]
Continuity = Literal["CONTINUOUS", "PARTIAL", "UNKNOWN"]
EstimatorCategory = Literal[
    "TOP_BAR",
    "TOP_BAR_EXTRA",
    "BOTTOM_BAR",
    "BOTTOM_BAR_EXTRA",
    "UNCLASSIFIED",
]


class LongitudinalBarClassifier:
    """Combine position + continuity into estimator reinforcement category."""

    def classify(
        self, position: Position, continuity: Continuity
    ) -> Tuple[EstimatorCategory, int]:
        if position == "TOP" and continuity == "CONTINUOUS":
            return "TOP_BAR", 90
        if position == "TOP" and continuity == "PARTIAL":
            return "TOP_BAR_EXTRA", 85
        if position == "BOTTOM" and continuity == "CONTINUOUS":
            return "BOTTOM_BAR", 90
        if position == "BOTTOM" and continuity == "PARTIAL":
            return "BOTTOM_BAR_EXTRA", 85
        if position == "TOP":
            return "TOP_BAR", 60
        if position == "BOTTOM":
            return "BOTTOM_BAR", 60
        return "UNCLASSIFIED", 40
