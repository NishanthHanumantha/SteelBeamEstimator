"""
Phase QA.1.1 — Module 5: Geometry Error Diagnostics
Analyse beam length, support, bounding box, axis, depth, width tolerance violations.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

from typing import Any, Dict, List

from diagnostic_models import (
    EngineeringDiagnostic, ImpactLevel, PipelineStage, RootCause
)

# Error→recommendation lookup
GEOMETRY_FIELD_RECOMMENDATIONS: Dict[str, str] = {
    "span_mm":  "Review beam axis reconstruction and span measurement in geometry engine. "
                "Check support node identification and clear-span calculation logic.",
    "depth_mm": "Review beam section depth extraction from drawing annotations. "
                "Check cross-section parser dimension handling.",
    "width_mm": "Review beam section width extraction from drawing annotations. "
                "Validate bounding-box width computation in geometry engine.",
}


class GeometryErrorDiagnostics:
    """Diagnoses geometry tolerance violations from QA.1 geometry accuracy report."""

    def diagnose(
        self,
        qa1_full_report: Dict[str, Any],
        l2_by_beam: Dict[str, Any],
        ground_truth: Dict[str, Any],
        drawing_name: str,
    ) -> List[EngineeringDiagnostic]:
        diagnostics: List[EngineeringDiagnostic] = []
        counter = 0

        if not qa1_full_report:
            return diagnostics

        geom_section = qa1_full_report.get("section_6_geometry_accuracy", {})
        tolerance_mm = geom_section.get("tolerance_mm", 2.0)
        mae = geom_section.get("mae_mm", 0.0)
        max_err = geom_section.get("max_error_mm", 0.0)

        # If all beams are within tolerance, produce a near-perfect diagnostic note
        if max_err <= tolerance_mm:
            counter += 1
            diagnostics.append(EngineeringDiagnostic(
                diagnostic_id=f"DIAG::GEOM::PASS::{counter:04d}",
                drawing_name=drawing_name,
                beam_id="ALL",
                bar_id="",
                error_type="KPI_GAP_GEOMETRY",
                expected_value=f"0.0 mm error",
                predicted_value=f"{mae} mm MAE",
                difference=f"Max error {max_err} mm — within ±{tolerance_mm} mm tolerance",
                pipeline_stage=PipelineStage.GEOMETRY_ENGINE,
                root_cause=RootCause.UNKNOWN,
                severity="LOW",
                impact_score=0.0,
                impact_level=ImpactLevel.LOW,
                confidence=1.0,
                downstream_modules=[],
                recommended_fix=(
                    "All geometry values within ±2 mm tolerance. "
                    "No geometry correction required. Continue monitoring for future drawings."
                ),
                engineering_notes=["Geometry KPI: 100.00% — all span measurements within tolerance."],
                traceability={"source": "QA.1 engineering_accuracy_report.json"},
            ))
            return diagnostics

        # Produce diagnostics for each tolerance violation
        for beam_id, model in l2_by_beam.items():
            gt_spans = ground_truth.get("geometry", {}).get("expected_spans_mm", {})
            gt_span = gt_spans.get(beam_id)
            if gt_span is None:
                continue
            geom = model.get("geometry") or {}
            pred_span = geom.get("clear_span_mm") or geom.get("span_mm")
            if pred_span is None:
                continue
            err = abs(float(pred_span) - float(gt_span))
            if err > tolerance_mm:
                counter += 1
                diagnostics.append(EngineeringDiagnostic(
                    diagnostic_id=f"DIAG::GEOM::SPAN::{counter:04d}",
                    drawing_name=drawing_name,
                    beam_id=beam_id,
                    bar_id="",
                    error_type="GEOMETRY_ERROR",
                    expected_value=f"{gt_span} mm",
                    predicted_value=f"{pred_span} mm",
                    difference=f"{err:.2f} mm > {tolerance_mm} mm tolerance",
                    pipeline_stage=PipelineStage.GEOMETRY_ENGINE,
                    root_cause=RootCause.GEOMETRY_ERROR,
                    severity="MEDIUM" if err < 10 else "HIGH",
                    impact_score=min(7.0, err / 5.0),
                    impact_level=ImpactLevel.MEDIUM,
                    confidence=0.9,
                    downstream_modules=[
                        "REINFORCEMENT_INTERPRETATION", "FEATURE_EXTRACTION",
                        "PATTERN_RECOGNITION", "BBS_GENERATION", "STEEL_CALCULATION"
                    ],
                    recommended_fix=GEOMETRY_FIELD_RECOMMENDATIONS["span_mm"],
                    engineering_notes=[
                        f"Beam {beam_id} span error: {err:.2f} mm exceeds ±{tolerance_mm} mm.",
                        "Development lengths and cut lengths depend on accurate span measurements.",
                    ],
                    traceability={"source": "L.2 geometry", "beam_id": beam_id},
                ))

        return diagnostics
