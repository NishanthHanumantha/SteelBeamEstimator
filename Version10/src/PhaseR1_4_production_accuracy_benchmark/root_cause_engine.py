"""
Root-cause attribution for benchmark mismatches.
MODEL_VERSION: 8.6.0
"""
from __future__ import annotations

from typing import Any, Dict, List

MODEL_VERSION = "8.6.0"

_PHASE_MAP = {
    "Missing Beam": ("Annotation", 0.7, "Verify annotation discovery emits every beam mark present on drawing."),
    "Extra Beam": ("Annotation", 0.55, "Filter spurious beam IDs before intent/detail generation."),
    "Missing Reinforcement Row": ("Intent", 0.65, "Check role resolution / detail generation for missing official roles."),
    "Wrong Classification": ("Intent", 0.7, "Improve terminology/role mapping between labels and TOP/BOTTOM/STIRRUP roles."),
    "Wrong Diameter": ("Detail", 0.7, "Trace diameter from annotation → intent → detail → piece."),
    "Wrong Quantity": ("Geometry", 0.6, "Validate GeometryProvider spans and bar counts against official breakup."),
    "Wrong Cut Length": ("Piece", 0.75, "Review piece cut-length formulas and support/zone expansion."),
    "Wrong Piece Type": ("Piece", 0.7, "Align piece_type taxonomy with official reinforcement descriptions."),
    "Wrong Shape": ("Piece", 0.6, "Check fabrication/shape codes for stirrups and hooks."),
    "Wrong Steel": ("Steel", 0.8, "Audit unit weights, length aggregation, and diameter bucketing."),
    "Wrong Weight": ("Steel", 0.8, "Reconcile total kg vs diameter MT summary."),
    "Wrong BBS": ("BBS", 0.7, "Ensure all EngineeringBars propagate into BBS rows."),
    "Wrong Workbook Output": ("Workbook", 0.85, "Confirm V.B.1 Excel generation path and template population."),
}


class RootCauseEngine:
    def analyze(
        self,
        diagnostics: Dict[str, Any],
        comparison: Dict[str, Any],
        kpis: Dict[str, Any],
    ) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []
        for d in diagnostics.get("diagnostics") or []:
            et = d.get("error_type") or ""
            phase, conf, fix = _PHASE_MAP.get(
                et, ("Unknown", 0.4, "Inspect full pipeline trace for this entity.")
            )
            # confidence adjustments
            if et == "Wrong Steel":
                pct = float((comparison.get("steel_accuracy") or {}).get("pct_error") or 0)
                if pct > 30:
                    phase, conf = "Intent", min(0.85, conf + 0.1)
                    fix = "Large steel gap usually originates upstream (intent/detail/piece), not only Steel calc."
            findings.append({
                "entity": d.get("entity"),
                "error_type": et,
                "message": d.get("message"),
                "originating_phase": phase,
                "confidence": conf,
                "suggested_engineering_fix": fix,
            })

        phase_counts: Dict[str, int] = {}
        for f in findings:
            p = f["originating_phase"]
            phase_counts[p] = phase_counts.get(p, 0) + 1

        overall = float((kpis.get("kpis") or {}).get("KPI_12_overall_production_accuracy") or 0)
        primary = None
        if phase_counts:
            primary = max(phase_counts.items(), key=lambda x: x[1])[0]

        return {
            "model_version": MODEL_VERSION,
            "finding_count": len(findings),
            "phase_counts": phase_counts,
            "primary_originating_phase": primary,
            "overall_production_accuracy": overall,
            "findings": findings[:200],
        }
