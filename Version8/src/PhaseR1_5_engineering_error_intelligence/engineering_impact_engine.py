"""
Engineering impact estimation (0–1) and steel impact kg.
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from engineering_issue_model import RawFinding

MODEL_VERSION = "8.7.0"

# Relative steel-share weights by reinforcement category (deterministic priors)
_CATEGORY_STEEL_SHARE = {
    "Stirrup Interpretation": 0.18,
    "Hook Interpretation": 0.10,
    "Spacer Interpretation": 0.04,
    "Side Face Reinforcement": 0.03,
    "Role Classification": 0.22,
    "Diameter Interpretation": 0.15,
    "Cut Length": 0.12,
    "Steel Aggregation": 0.25,
    "Weight Calculation": 0.20,
    "Beam Discovery": 0.08,
    "Annotation Association": 0.04,
    "Piece Generation": 0.10,
    "Workbook Export": 0.02,
    "Quantity Interpretation": 0.08,
    "Development Length": 0.06,
    "Support Zone Interpretation": 0.08,
    "Curtailment": 0.07,
    "Continuity": 0.05,
    "Unknown": 0.05,
}


class EngineeringImpactEngine:
    def estimate(
        self,
        category: str,
        findings: List[RawFinding],
        official_total_kg: float,
        steel_gap_kg: float,
        total_findings: int,
        kpi_loss: float,
    ) -> Dict[str, float]:
        freq = len(findings)
        freq_share = freq / max(1, total_findings)
        share = _CATEGORY_STEEL_SHARE.get(category, 0.05)

        # Allocate steel gap proportionally to frequency × category share
        steel_impact = abs(steel_gap_kg) * share * (0.35 + 0.65 * freq_share)
        # Cap at steel gap
        steel_impact = min(steel_impact, abs(steel_gap_kg))

        weight_pct = (steel_impact / official_total_kg * 100.0) if official_total_kg > 0 else 0.0

        # Accuracy loss attribution (portion of overall KPI gap)
        accuracy_loss = max(0.0, kpi_loss) * (0.4 * share + 0.6 * freq_share)
        accuracy_loss = min(1.0, accuracy_loss)

        # Component impacts 0–1
        steel_n = min(1.0, steel_impact / max(1.0, abs(steel_gap_kg) or 1.0))
        weight_n = min(1.0, weight_pct / 30.0)
        bbs_n = 0.7 if category in ("Steel Aggregation", "Piece Generation", "Stirrup Interpretation") else 0.2 * freq_share
        workbook_n = 1.0 if category == "Workbook Export" else 0.0
        class_n = min(1.0, freq_share * 1.5) if "Role" in category or category in (
            "Stirrup Interpretation", "Hook Interpretation", "Spacer Interpretation",
            "Side Face Reinforcement",
        ) else 0.15 * freq_share
        detect_n = min(1.0, freq / 4.0) if category in ("Beam Discovery", "Annotation Association") else 0.1 * freq_share

        engineering_impact = round(
            0.30 * steel_n
            + 0.15 * weight_n
            + 0.20 * accuracy_loss
            + 0.10 * bbs_n
            + 0.05 * workbook_n
            + 0.12 * class_n
            + 0.08 * detect_n,
            4,
        )
        engineering_impact = max(0.0, min(1.0, engineering_impact))

        return {
            "engineering_impact": engineering_impact,
            "steel_impact_kg": round(steel_impact, 3),
            "weight_percentage": round(weight_pct, 3),
            "production_accuracy_loss": round(accuracy_loss, 4),
            "steel_impact_norm": round(steel_n, 4),
            "bbs_impact": round(bbs_n, 4),
            "workbook_impact": round(workbook_n, 4),
            "classification_impact": round(class_n, 4),
            "detection_impact": round(detect_n, 4),
        }
