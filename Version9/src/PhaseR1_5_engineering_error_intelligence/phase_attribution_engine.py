"""
Single originating-phase attribution per issue.
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

from collections import Counter
from typing import List

from engineering_issue_model import ALLOWED_PHASES, RawFinding

MODEL_VERSION = "8.7.0"

_CATEGORY_PHASE = {
    "Beam Discovery": "Annotation",
    "Annotation Association": "Annotation",
    "Role Classification": "Intent",
    "Diameter Interpretation": "Detail",
    "Quantity Interpretation": "Fact",
    "Development Length": "Detail",
    "Cut Length": "Piece",
    "Support Zone Interpretation": "Detail",
    "Curtailment": "Detail",
    "Continuity": "Detail",
    "Stirrup Interpretation": "Detail",
    "Hook Interpretation": "Detail",
    "Spacer Interpretation": "Intent",
    "Side Face Reinforcement": "Detail",
    "Piece Generation": "Piece",
    "Steel Aggregation": "Steel",
    "Weight Calculation": "Steel",
    "Workbook Export": "Workbook",
    "Unknown": "Intent",
}

# Map R.1.4 phase names to allowed R.1.5 phases
_PHASE_NORMALIZE = {
    "Annotation": "Annotation",
    "Geometry": "Fact",
    "Fact": "Fact",
    "Intent": "Intent",
    "Detail": "Detail",
    "Piece": "Piece",
    "EngineeringBar": "EngineeringBar",
    "Steel": "Steel",
    "BBS": "Steel",
    "Workbook": "Workbook",
    "Unknown": "Intent",
}


class PhaseAttributionEngine:
    def attribute(self, category: str, findings: List[RawFinding]) -> str:
        """Exactly one originating phase."""
        votes = Counter()
        for f in findings:
            p = _PHASE_NORMALIZE.get(f.originating_phase, "")
            if p in ALLOWED_PHASES:
                votes[p] += 1
        if votes:
            # majority vote; ties broken by category default then alphabetical
            top = votes.most_common()
            best_count = top[0][1]
            candidates = sorted([p for p, c in top if c == best_count])
            default = self.default_phase(category)
            if default in candidates:
                return default
            return candidates[0]
        return self.default_phase(category)

    @staticmethod
    def default_phase(category: str) -> str:
        phase = _CATEGORY_PHASE.get(category, "Intent")
        if phase not in ALLOWED_PHASES:
            phase = "Intent"
        return phase
