"""
Phase QA.1.1 — Module 9 (Steel): Steel Weight Error Diagnostics
Analyse steel weight mismatches, propagation from BBS and diameter errors.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

from typing import Any, Dict, List

from diagnostic_models import (
    EngineeringDiagnostic, ImpactLevel, PipelineStage, RootCause
)


class SteelErrorDiagnostics:
    """Diagnoses steel weight errors. May be deferred if V5 steel weight is not available."""

    def diagnose(
        self,
        qa1_summary: Dict[str, Any],
        qa1_full_report: Dict[str, Any],
        drawing_name: str,
    ) -> List[EngineeringDiagnostic]:
        diagnostics: List[EngineeringDiagnostic] = []
        counter = 0

        steel_acc = qa1_summary.get("steel_weight_accuracy")

        if steel_acc is None:
            # Steel weight not computed — V5 deferred
            counter += 1
            diagnostics.append(EngineeringDiagnostic(
                diagnostic_id=f"DIAG::STEEL::NOT_AVAILABLE::{counter:04d}",
                drawing_name=drawing_name,
                beam_id="ALL",
                bar_id="",
                error_type="KPI_GAP_STEEL_WEIGHT",
                expected_value="N/A — V5 steel weight not computed",
                predicted_value="N/A",
                difference="Steel weight KPI unavailable for this drawing",
                pipeline_stage=PipelineStage.STEEL_CALCULATION,
                root_cause=RootCause.REFERENCE_DATA_ERROR,
                severity="LOW",
                impact_score=1.5,
                impact_level=ImpactLevel.LOW,
                confidence=1.0,
                downstream_modules=[],
                recommended_fix=(
                    "Steel weight accuracy cannot be measured because V5 pipeline "
                    "does not provide a steel weight result for this drawing. "
                    "Run Phase I (V5) to completion for benchmark drawings or "
                    "provide manual steel weight ground truth in the benchmark JSON. "
                    "Add 'steel_weight': {'expected_total_kg': <value>} to benchmark_drawing_1.json."
                ),
                engineering_notes=[
                    "V5 Phase I steel weight calculation was not completed for this drawing.",
                    "This KPI will remain NOT_AVAILABLE until V5 results are provided.",
                    "BBS diameter errors (5 errors in QA.1) will affect steel weight when computed.",
                ],
                traceability={
                    "source": "QA.1 engineering_accuracy_summary.json",
                    "note": "steel_weight_accuracy = null",
                },
            ))
            return diagnostics

        # If steel weight is available, compute gap diagnostics
        gap = 100.0 - float(steel_acc)
        if gap > 0.0:
            counter += 1
            diagnostics.append(EngineeringDiagnostic(
                diagnostic_id=f"DIAG::STEEL::KPI_GAP::{counter:04d}",
                drawing_name=drawing_name,
                beam_id="ALL",
                bar_id="",
                error_type="KPI_GAP_STEEL_WEIGHT",
                expected_value="100.0%",
                predicted_value=f"{steel_acc:.4f}%",
                difference=f"Gap: {gap:.4f}%",
                pipeline_stage=PipelineStage.STEEL_CALCULATION,
                root_cause=RootCause.CALCULATION_ERROR,
                severity="MEDIUM" if gap < 5.0 else "HIGH",
                impact_score=min(9.0, gap * 0.5),
                impact_level=ImpactLevel.HIGH if gap > 5 else ImpactLevel.MEDIUM,
                confidence=0.85,
                downstream_modules=[],
                recommended_fix=(
                    "Steel weight computation error detected. "
                    "Verify: (1) density constant (7850 kg/m³ for steel), "
                    "(2) diameter-to-area lookup table, "
                    "(3) cut length used for weight computation, "
                    "(4) quantity per bar entry in BBS schedule."
                ),
                engineering_notes=[
                    f"Steel weight accuracy: {steel_acc:.2f}%.",
                    "Error may propagate from BBS diameter or cut length mismatches.",
                ],
                traceability={"source": "QA.1 engineering_accuracy_summary.json"},
            ))

        return diagnostics
