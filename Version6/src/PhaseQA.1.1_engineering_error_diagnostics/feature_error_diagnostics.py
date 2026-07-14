"""
Phase QA.1.1 — Module 6: Feature Error Diagnostics
Analyse top/bottom/side/stirrups/orientation/coverage/support/continuity features.
Detect feature propagation failures.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

from typing import Any, Dict, List

from diagnostic_models import (
    EngineeringDiagnostic, ImpactLevel, PipelineStage, RootCause
)


class FeatureErrorDiagnostics:
    """Diagnoses feature-level errors from QA.1 feature accuracy KPI."""

    def diagnose(
        self,
        qa1_summary: Dict[str, Any],
        l21_by_beam: Dict[str, Any],
        l2_by_beam: Dict[str, Any],
        ground_truth: Dict[str, Any],
        drawing_name: str,
    ) -> List[EngineeringDiagnostic]:
        diagnostics: List[EngineeringDiagnostic] = []
        counter = 0

        feature_acc = qa1_summary.get("feature_accuracy", 100.0) or 100.0
        top_bottom_acc = qa1_summary.get("top_bottom_accuracy", 100.0) or 100.0

        # ── Feature extraction KPI gap ─────────────────────────────────────
        if feature_acc < 100.0:
            gap = 100.0 - feature_acc
            counter += 1
            diagnostics.append(EngineeringDiagnostic(
                diagnostic_id=f"DIAG::FEAT::FEATURE_COUNT::{counter:04d}",
                drawing_name=drawing_name,
                beam_id="MULTIPLE",
                bar_id="",
                error_type="KPI_GAP_FEATURE_EXTRACTION",
                expected_value="100.0%",
                predicted_value=f"{feature_acc:.4f}%",
                difference=f"Gap: {gap:.4f}%",
                pipeline_stage=PipelineStage.FEATURE_EXTRACTION,
                root_cause=RootCause.FEATURE_ERROR,
                severity="MEDIUM" if gap < 15 else "HIGH",
                impact_score=min(8.0, gap * 0.3),
                impact_level=ImpactLevel.MEDIUM if gap < 20 else ImpactLevel.HIGH,
                confidence=0.9,
                downstream_modules=["PATTERN_RECOGNITION", "BBS_GENERATION"],
                recommended_fix=(
                    "Feature extraction accuracy is below 100%. "
                    "Review bar-to-feature mapping rules in Phase L.2.1. "
                    "Ensure that each bar role (TOP_MAIN, BOTTOM_MAIN, STIRRUP, SIDE_FACE) "
                    "generates a corresponding engineering feature entry. "
                    "Check zone assignment logic for side face reinforcement bars."
                ),
                engineering_notes=[
                    f"Feature accuracy: {feature_acc:.2f}% — {gap:.2f}% gap from perfect.",
                    "Feature database may be missing entries for some beams.",
                    "Pattern recognition depends on complete feature coverage.",
                ],
                traceability={
                    "source": "QA.1 engineering_accuracy_summary.json",
                    "kpi": "feature_accuracy",
                },
            ))

        # ── Top/Bottom classification KPI gap ─────────────────────────────
        if top_bottom_acc < 100.0:
            gap = 100.0 - top_bottom_acc
            counter += 1

            # Identify beams with top/bottom errors by checking L.2 roles vs GT
            affected_beams = []
            gt_tb = ground_truth.get("top_bottom", {})
            for bid, model in l2_by_beam.items():
                gt_entry = gt_tb.get(bid, {})
                if not gt_entry:
                    continue
                by_role = model.get("bar_count_by_role", {})
                has_top = (by_role.get("TOP_MAIN", 0) + by_role.get("TOP_EXTRA", 0)) > 0
                has_bottom = (by_role.get("BOTTOM_MAIN", 0) + by_role.get("BOTTOM_EXTRA", 0)) > 0
                expected_top = gt_entry.get("expected_top", 0) > 0
                expected_bottom = gt_entry.get("expected_bottom", 0) > 0
                if has_top != expected_top or has_bottom != expected_bottom:
                    affected_beams.append(bid)

            diagnostics.append(EngineeringDiagnostic(
                diagnostic_id=f"DIAG::FEAT::TOP_BOTTOM::{counter:04d}",
                drawing_name=drawing_name,
                beam_id=",".join(affected_beams) if affected_beams else "MULTIPLE",
                bar_id="",
                error_type="KPI_GAP_TOP_BOTTOM",
                expected_value="100.0%",
                predicted_value=f"{top_bottom_acc:.4f}%",
                difference=f"Gap: {gap:.4f}%",
                pipeline_stage=PipelineStage.REINFORCEMENT_INTERPRETATION,
                root_cause=RootCause.ASSOCIATION_ERROR,
                severity="MEDIUM" if gap < 20 else "HIGH",
                impact_score=min(8.0, gap * 0.35),
                impact_level=ImpactLevel.MEDIUM if gap < 25 else ImpactLevel.HIGH,
                confidence=0.88,
                downstream_modules=[
                    "FEATURE_EXTRACTION", "PATTERN_RECOGNITION",
                    "BBS_GENERATION", "STEEL_CALCULATION"
                ],
                recommended_fix=(
                    "Top/Bottom classification gap detected in Phase L.2. "
                    "Review top/bottom bar role assignment heuristics in the engineering "
                    "reinforcement interpretation engine. "
                    "Check vertical position thresholds used to classify bars as top vs bottom. "
                    f"Affected beams: {affected_beams or 'see QA.1 top/bottom report'}."
                ),
                engineering_notes=[
                    f"Top/Bottom accuracy: {top_bottom_acc:.2f}% — {gap:.2f}% gap.",
                    "Misclassification leads to incorrect moment zone identification.",
                    "BBS scheduling may assign wrong shapes to top vs bottom bars.",
                ],
                traceability={
                    "source": "QA.1 engineering_accuracy_summary.json",
                    "kpi": "top_bottom_accuracy",
                    "affected_beams": affected_beams,
                },
            ))

            # Beam-level top/bottom diagnostics
            for bid in affected_beams:
                counter += 1
                model = l2_by_beam.get(bid, {})
                by_role = model.get("bar_count_by_role", {})
                gt_entry = gt_tb.get(bid, {})
                diagnostics.append(EngineeringDiagnostic(
                    diagnostic_id=f"DIAG::FEAT::TOP_BOTTOM_BEAM::{counter:04d}",
                    drawing_name=drawing_name,
                    beam_id=bid,
                    bar_id="",
                    error_type="TOP_BOTTOM_ERROR",
                    expected_value=(
                        f"Top={gt_entry.get('expected_top')}, "
                        f"Bottom={gt_entry.get('expected_bottom')}"
                    ),
                    predicted_value=(
                        f"Top={by_role.get('TOP_MAIN',0)+by_role.get('TOP_EXTRA',0)}, "
                        f"Bottom={by_role.get('BOTTOM_MAIN',0)+by_role.get('BOTTOM_EXTRA',0)}"
                    ),
                    difference="Top/bottom count mismatch",
                    pipeline_stage=PipelineStage.REINFORCEMENT_INTERPRETATION,
                    root_cause=RootCause.ASSOCIATION_ERROR,
                    severity="MEDIUM",
                    impact_score=4.5,
                    impact_level=ImpactLevel.MEDIUM,
                    confidence=0.85,
                    downstream_modules=["FEATURE_EXTRACTION", "PATTERN_RECOGNITION", "BBS_GENERATION"],
                    recommended_fix=(
                        f"Beam {bid}: review bar vertical position threshold in L.2. "
                        "Ensure neutral-axis heuristic correctly partitions top vs bottom bars."
                    ),
                    engineering_notes=[f"Beam {bid} top/bottom classification incorrect."],
                    traceability={
                        "beam_id": bid,
                        "l2_by_role": dict(by_role),
                        "gt_top_bottom": dict(gt_entry),
                    },
                ))

        return diagnostics
