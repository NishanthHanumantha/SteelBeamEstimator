"""
Expected improvement estimates per rule.
MODEL_VERSION: 8.8.0
"""
from __future__ import annotations

from typing import Any, Dict, List

MODEL_VERSION = "8.8.0"


class ExpectedGainEngine:
    def for_pattern(self, issues: List[Dict[str, Any]]) -> Dict[str, float]:
        # Sum attributed gains but cap to avoid absurd totals; steel sum similarly
        acc = sum(float(i.get("expected_accuracy_gain") or 0.0) for i in issues)
        steel = sum(float(i.get("steel_impact_kg") or 0.0) for i in issues)
        confs = [float(i.get("confidence") or 0.5) for i in issues]
        conf = sum(confs) / len(confs) if confs else 0.5
        beams = set()
        for i in issues:
            beams.update(i.get("affected_beams") or [])
        roles = set()
        for i in issues:
            roles.update(i.get("affected_roles") or [])
        return {
            "expected_accuracy_gain": round(acc, 2),
            "estimated_steel_gain_kg": round(steel, 3),
            "beam_gain": float(len(beams)),
            "classification_gain": round(min(1.0, len(roles) * 0.15 + len(issues) * 0.1), 4),
            "diameter_gain": round(0.15 if any("Diameter" in (i.get("category") or "") for i in issues) else 0.05, 4),
            "bbs_gain": round(0.2 if any(
                (i.get("category") or "") in ("Stirrup Interpretation", "Steel Aggregation", "Hook Interpretation")
                for i in issues
            ) else 0.05, 4),
            "workbook_gain": round(0.1 if any("Workbook" in (i.get("category") or "") for i in issues) else 0.02, 4),
            "confidence": round(conf, 4),
        }
