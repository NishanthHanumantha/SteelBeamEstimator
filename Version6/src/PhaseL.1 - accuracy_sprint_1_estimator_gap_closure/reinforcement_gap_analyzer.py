"""Role-level reinforcement gap table."""

from __future__ import annotations

from typing import Any, Dict, List


REINFORCEMENT_ROLES = [
    "TOP_MAIN", "BOTTOM_MAIN", "TOP_EXTRA", "BOTTOM_EXTRA",
    "STIRRUP", "SIDE_FACE_REINFORCEMENT", "SPACER_BAR",
    "CHAIR_BAR", "SUPPLEMENTARY_BAR", "UNKNOWN",
]

ROLE_ROOT_CAUSE: Dict[str, str] = {
    "TOP_MAIN": "Partial RULE_GAP — intent reconstructed for most beams but not all",
    "BOTTOM_MAIN": "RULE_GAP — no bottom main engineering rule implemented",
    "TOP_EXTRA": "RULE_GAP — no top extra (negative moment redistribution) rule implemented",
    "BOTTOM_EXTRA": "RULE_GAP — no bottom extra (positive moment extra) rule implemented",
    "STIRRUP": "RULE_GAP — no stirrup/shear link engineering rule implemented",
    "SIDE_FACE_REINFORCEMENT": "RULE_GAP — side face reinforcement rule absent",
    "SPACER_BAR": "RULE_GAP — spacer bar rule may be partially covered by spec but not scheduled",
    "CHAIR_BAR": "RULE_GAP — chair bar rule absent",
    "SUPPLEMENTARY_BAR": "DECISION_GAP — supplementary bars resolved in K.1.1 but calculations pending",
    "UNKNOWN": "UNKNOWN — insufficient evidence for classification",
}

ROLE_PRIORITY: Dict[str, str] = {
    "TOP_MAIN": "HIGH",
    "BOTTOM_MAIN": "CRITICAL",
    "TOP_EXTRA": "CRITICAL",
    "BOTTOM_EXTRA": "CRITICAL",
    "STIRRUP": "CRITICAL",
    "SIDE_FACE_REINFORCEMENT": "HIGH",
    "SPACER_BAR": "MEDIUM",
    "CHAIR_BAR": "MEDIUM",
    "SUPPLEMENTARY_BAR": "HIGH",
    "UNKNOWN": "LOW",
}

ROLE_FUTURE_PHASE: Dict[str, str] = {
    "TOP_MAIN": "Phase L.2 — fix partial coverage",
    "BOTTOM_MAIN": "Phase L.2 — implement bottom main rule",
    "TOP_EXTRA": "Phase L.2 — implement top extra rule",
    "BOTTOM_EXTRA": "Phase L.2 — implement bottom extra rule",
    "STIRRUP": "Phase L.2 — implement stirrup rule",
    "SIDE_FACE_REINFORCEMENT": "Phase L.2",
    "SPACER_BAR": "Phase L.2",
    "CHAIR_BAR": "Phase L.3",
    "SUPPLEMENTARY_BAR": "Phase L.2 — run full pipeline",
    "UNKNOWN": "Phase L.3",
}


class ReinforcementGapAnalyzer:
    """Build role-level gap table comparing estimator vs model."""

    def analyze(
        self,
        comparison: Dict[str, Any],
        snapshot: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        est = snapshot.get("estimator_data") or {}
        decisions = snapshot.get("decisions") or []
        all_rows = est.get("rows") or []

        # Count estimator bars by role
        est_counts: Dict[str, Dict[str, Any]] = {}
        for row in all_rows:
            role = self._normalise_role(str(row.get("role_hint") or ""))
            entry = est_counts.setdefault(role, {
                "role": role,
                "estimator_bar_count": 0,
                "estimator_weight_kg": 0.0,
                "estimator_row_count": 0,
                "beams_with_role": set(),
            })
            entry["estimator_bar_count"] += int(row.get("bar_count") or 0)
            entry["estimator_weight_kg"] += float(row.get("steel_weight_kg") or 0.0)
            entry["estimator_row_count"] += 1
            beam = row.get("beam_mark")
            if beam:
                entry["beams_with_role"].add(str(beam))

        # Count model decisions by role proxy
        model_counts: Dict[str, int] = {}
        for d in decisions:
            cat = str(d.get("decision_category") or "UNKNOWN")
            role = self._decision_to_role(cat)
            model_counts[role] = model_counts.get(role, 0) + 1

        result: List[Dict[str, Any]] = []
        for role in REINFORCEMENT_ROLES:
            est_entry = est_counts.get(role, {})
            est_count = est_entry.get("estimator_bar_count", 0)
            est_weight = round(float(est_entry.get("estimator_weight_kg", 0.0)), 3)
            est_row_count = est_entry.get("estimator_row_count", 0)
            est_beams = sorted(est_entry.get("beams_with_role", set()))
            model_count = model_counts.get(role, 0)
            diff = est_count - model_count
            cov = round(100 * model_count / max(est_count, 1), 2) if est_count > 0 else 0.0
            result.append({
                "role": role,
                "estimator_bar_count": est_count,
                "estimator_weight_kg": est_weight,
                "estimator_row_count": est_row_count,
                "estimator_beams": est_beams,
                "model_decision_count": model_count,
                "difference": diff,
                "coverage_percent": cov,
                "root_cause": ROLE_ROOT_CAUSE.get(role, "UNKNOWN"),
                "priority": ROLE_PRIORITY.get(role, "MEDIUM"),
                "future_phase": ROLE_FUTURE_PHASE.get(role, "Phase L.2"),
            })
        return result

    @staticmethod
    def _normalise_role(hint: str) -> str:
        h = hint.lower().strip()
        if "top" in h and ("extra" in h or "add" in h):
            return "TOP_EXTRA"
        if "bottom" in h and ("extra" in h or "add" in h):
            return "BOTTOM_EXTRA"
        if "top" in h and "main" in h:
            return "TOP_MAIN"
        if "bottom" in h and "main" in h:
            return "BOTTOM_MAIN"
        if "top" in h:
            return "TOP_MAIN"
        if "bottom" in h:
            return "BOTTOM_MAIN"
        if "stirrup" in h or "link" in h or "shear" in h:
            return "STIRRUP"
        if "side" in h or "face" in h:
            return "SIDE_FACE_REINFORCEMENT"
        if "spacer" in h:
            return "SPACER_BAR"
        if "chair" in h:
            return "CHAIR_BAR"
        if "supplementary" in h or "extra" in h:
            return "SUPPLEMENTARY_BAR"
        return "UNKNOWN"

    @staticmethod
    def _decision_to_role(category: str) -> str:
        c = category.upper()
        if "SUPPORT_REINFORCEMENT" in c and "CONTINUOUS" not in c:
            return "BOTTOM_MAIN"
        if "CONTINUOUS_SUPPORT" in c:
            return "TOP_MAIN"
        if "SUPPLEMENTARY" in c:
            return "SUPPLEMENTARY_BAR"
        return "UNKNOWN"
