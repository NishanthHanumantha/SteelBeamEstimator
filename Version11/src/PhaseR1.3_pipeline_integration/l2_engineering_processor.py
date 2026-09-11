"""L.2 Engineering Processing Layer — validation without REFERENCE_CLASSIFICATION."""
from __future__ import annotations
from typing import Any, Dict, List

from .engineering_bar_model import BeamEngineeringModel, EngineeringBarModel


class L2EngineeringProcessor:
    """
    Engineering processing responsibilities:
      - engineering validation
      - role refinement
      - consistency checks
      - engineering normalization
    No benchmark beam filtering.
    """

    VALID_ROLES = {
        "TOP_MAIN", "BOTTOM_MAIN", "TOP_EXTRA", "BOTTOM_EXTRA",
        "STIRRUP", "SPACER_BAR", "SIDE_FACE_REINFORCEMENT",
        "DEVELOPMENT", "LAP", "UNKNOWN",
    }

    def process(self, beam_models: List[BeamEngineeringModel]) -> Dict[str, Any]:
        report = {
            "beams_processed": len(beam_models),
            "bars_validated": 0,
            "bars_normalized": 0,
            "consistency_issues": [],
            "role_counts": {},
            "diameter_counts": {},
        }

        for bm in beam_models:
            for bar in bm.bars:
                report["bars_validated"] += 1
                bar = self._normalize_bar(bar)
                report["bars_normalized"] += 1
                report["role_counts"][bar.bar_role] = (
                    report["role_counts"].get(bar.bar_role, 0) + 1
                )
                dia_key = str(int(bar.diameter_mm))
                report["diameter_counts"][dia_key] = (
                    report["diameter_counts"].get(dia_key, 0) + bar.quantity
                )
                issues = self._check_consistency(bar)
                report["consistency_issues"].extend(issues)

        report["reference_classification_used"] = False
        return report

    def _normalize_bar(self, bar: EngineeringBarModel) -> EngineeringBarModel:
        if bar.bar_role not in self.VALID_ROLES:
            bar.bar_role = "UNKNOWN"
        if bar.quantity < 1:
            bar.quantity = 1
        if bar.diameter_mm <= 0:
            bar.diameter_mm = 8.0
        return bar

    def _check_consistency(self, bar: EngineeringBarModel) -> List[str]:
        issues = []
        if bar.bar_role == "STIRRUP" and bar.spacing_mm is None:
            issues.append(f"{bar.beam_id}: stirrup missing spacing")
        if bar.quantity <= 0:
            issues.append(f"{bar.beam_id}: zero quantity for {bar.bar_role}")
        return issues
