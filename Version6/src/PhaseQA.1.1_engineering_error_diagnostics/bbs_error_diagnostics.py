"""
Phase QA.1.1 — Module 8: BBS Error Diagnostics
Analyse diameter, shape, quantity, cut length, hooks, bent length, schedule mismatches.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from diagnostic_models import (
    EngineeringDiagnostic, ImpactLevel, PipelineStage, RootCause
)

# Root cause determined by mismatch field
FIELD_ROOT_CAUSE: Dict[str, str] = {
    "diameter":   RootCause.REFERENCE_DATA_ERROR,   # V5 diameter ≠ L.2 diameter
    "cut_length": RootCause.CALCULATION_ERROR,       # cut length formula error
    "shape":      RootCause.BBS_ERROR,
    "quantity":   RootCause.ASSOCIATION_ERROR,
    "hooks":      RootCause.BBS_ERROR,
    "bent_length": RootCause.CALCULATION_ERROR,
}

FIELD_RECOMMENDATION: Dict[str, str] = {
    "diameter": (
        "Diameter mismatch between V5 BBS schedule and L.2 bar model. "
        "Review BBS-to-bar role mapping: ensure the diameter stored in V5 Phase I "
        "matches the diameter_mm field of the corresponding L.2 bar role. "
        "Cross-check drawing rebar schedule for correct diameter annotation."
    ),
    "cut_length": (
        "Cut length mismatch in BBS schedule. "
        "Review the cut length formula parameters (development length, hook allowances, "
        "bend allowances). Validate against IS 2502 / IS 456 provisions."
    ),
    "shape": (
        "Bar shape code mismatch. "
        "Review shape code assignment rules in BBS generation engine. "
        "Validate against IS 2502 shape code definitions."
    ),
    "quantity": (
        "Quantity mismatch in BBS schedule. "
        "Review bar grouping and member-beam association rules. "
        "Ensure multi-span bars are not double-counted."
    ),
    "hooks": (
        "Hook configuration mismatch. "
        "Review hook generation logic for anchorage and lapping conditions. "
        "Validate against IS 456 standard hook requirements."
    ),
    "bent_length": (
        "Bent length mismatch. "
        "Review bend radius and pin diameter parameters in BBS calculation. "
        "Validate against IS 2502 bend allowance tables."
    ),
}


class BBSErrorDiagnostics:
    """Diagnoses BBS schedule errors from QA.1 error_analysis and bbs_accuracy_report."""

    def diagnose(
        self,
        qa1_errors: Dict[str, Any],
        qa1_bbs_report: Dict[str, Any],
        v5_bbs_by_beam: Dict[str, List[Dict[str, Any]]],
        l2_by_beam: Dict[str, Any],
        drawing_name: str,
    ) -> List[EngineeringDiagnostic]:
        diagnostics: List[EngineeringDiagnostic] = []
        counter = 0

        # Primary: explicit BBS_ROW_ERROR entries from error_analysis.json
        for err in qa1_errors.get("highest_impact_errors", []):
            if err.get("error_type") != "BBS_ROW_ERROR":
                continue
            counter += 1
            bid = err.get("beam_id", "")
            desc = err.get("description", "")
            severity = err.get("severity", "LOW")
            impact_score = float(err.get("impact_score", 3.0))

            # Determine which field mismatched from description
            mismatch_field = "diameter"
            for field in FIELD_ROOT_CAUSE:
                if field in desc.lower():
                    mismatch_field = field
                    break

            # Get expected vs actual from L.2 and V5
            v5_entries = v5_bbs_by_beam.get(bid, [])
            l2_model = l2_by_beam.get(bid, {})

            # Extract BBS ID from description
            bbs_id = ""
            m = re.search(r"BBS::\d+", desc)
            if m:
                bbs_id = m.group(0)

            # Find the specific V5 BBS entry
            v5_entry = {}
            if bbs_id:
                for e in v5_entries:
                    if e.get("bbs_id", "").endswith(bbs_id.split("::")[-1]):
                        v5_entry = e
                        break

            expected_val = str(v5_entry.get(mismatch_field, "N/A")) if v5_entry else "see V5 BBS"
            pred_val = _find_l2_value(l2_model, mismatch_field)

            diagnostics.append(EngineeringDiagnostic(
                diagnostic_id=f"DIAG::BBS::ROW::{counter:04d}",
                drawing_name=drawing_name,
                beam_id=bid,
                bar_id=bbs_id,
                error_type="BBS_ROW_ERROR",
                expected_value=expected_val,
                predicted_value=pred_val,
                difference=f"Mismatch field: {mismatch_field}",
                pipeline_stage=PipelineStage.BBS_GENERATION,
                root_cause=FIELD_ROOT_CAUSE.get(mismatch_field, RootCause.BBS_ERROR),
                severity=severity,
                impact_score=impact_score,
                impact_level=ImpactLevel.from_score(impact_score),
                confidence=0.92,
                downstream_modules=["STEEL_CALCULATION"],
                recommended_fix=FIELD_RECOMMENDATION.get(mismatch_field, "Review BBS generation."),
                engineering_notes=[
                    f"BBS entry {bbs_id} for beam {bid}: {mismatch_field} mismatch.",
                    f"V5 BBS recorded: {expected_val}, L.2 model yields: {pred_val}.",
                    "Diameter discrepancies propagate to steel weight calculations.",
                ],
                traceability={
                    "source": "QA.1 error_analysis.json",
                    "bbs_id": bbs_id,
                    "beam_id": bid,
                    "mismatch_field": mismatch_field,
                    "v5_entry": v5_entry,
                },
            ))

        # Secondary: BBS KPI summary diagnostics
        if qa1_bbs_report:
            bbs_acc = qa1_bbs_report.get("bbs_accuracy_pct", 100.0) or 100.0
            if bbs_acc < 100.0:
                gap = 100.0 - bbs_acc
                counter += 1
                diagnostics.append(EngineeringDiagnostic(
                    diagnostic_id=f"DIAG::BBS::KPI_GAP::{counter:04d}",
                    drawing_name=drawing_name,
                    beam_id="MULTIPLE",
                    bar_id="",
                    error_type="KPI_GAP_BBS",
                    expected_value="100.0%",
                    predicted_value=f"{bbs_acc:.4f}%",
                    difference=f"Gap: {gap:.4f}%",
                    pipeline_stage=PipelineStage.BBS_GENERATION,
                    root_cause=RootCause.BBS_ERROR,
                    severity="MEDIUM" if gap < 30 else "HIGH",
                    impact_score=min(8.0, gap * 0.15),
                    impact_level=ImpactLevel.MEDIUM,
                    confidence=0.9,
                    downstream_modules=["STEEL_CALCULATION"],
                    recommended_fix=(
                        "BBS schedule accuracy is below 100%. "
                        "Primary gap in diameter field mapping. "
                        "Review V5 Phase I BBS diameter assignment from drawing annotations. "
                        "Ensure bar diameter assignment in BBS references the same "
                        "diameter_mm value as the L.2 reinforcement model."
                    ),
                    engineering_notes=[
                        f"BBS accuracy: {bbs_acc:.2f}% — {gap:.2f}% gap.",
                        "Root cause: diameter mapping mismatch between V5 BBS and L.2 model.",
                    ],
                    traceability={"source": "QA.1 bbs_accuracy_report.json"},
                ))

        return diagnostics


def _find_l2_value(l2_model: Dict[str, Any], field: str) -> str:
    """Extract a representative value from the L.2 model for the given BBS field."""
    if not l2_model:
        return "N/A"
    if field == "diameter":
        by_role = l2_model.get("bar_count_by_role", {})
        diameters = set()
        for role_bars in [
            l2_model.get("top_main_bars", []),
            l2_model.get("bottom_main_bars", []),
            l2_model.get("stirrup_bars", []),
        ]:
            for bar in role_bars:
                d = bar.get("diameter_mm")
                if d:
                    diameters.add(d)
        return str(sorted(diameters)) if diameters else "N/A"
    return "N/A"
