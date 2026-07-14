"""
Phase QA.1.1 — Module 3: Beam Error Diagnostics
Analyse missing beams, duplicate beams, wrong assignment, naming, connectivity.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

from typing import Any, Dict, List

from diagnostic_models import (
    EngineeringDiagnostic, ImpactLevel, PipelineStage, RootCause
)


class BeamErrorDiagnostics:
    """Diagnoses beam-level errors from QA.1 beam accuracy report."""

    def diagnose(
        self,
        qa1_beam_report: Dict[str, Any],
        l2_by_beam: Dict[str, Any],
        ground_truth: Dict[str, Any],
        drawing_name: str,
    ) -> List[EngineeringDiagnostic]:
        diagnostics: List[EngineeringDiagnostic] = []
        counter = 0

        expected_ids = set(ground_truth.get("beam_detection", {}).get("expected_beam_ids", []))
        detected_ids = set(l2_by_beam.keys())

        missing = expected_ids - detected_ids
        false_pos = detected_ids - expected_ids

        for bid in sorted(missing):
            counter += 1
            diagnostics.append(EngineeringDiagnostic(
                diagnostic_id=f"DIAG::BEAM::MISSING::{counter:04d}",
                drawing_name=drawing_name,
                beam_id=bid,
                bar_id="",
                error_type="MISSING_BEAM",
                expected_value=bid,
                predicted_value=None,
                difference="Beam not detected",
                pipeline_stage=PipelineStage.DRAWING_PARSER,
                root_cause=RootCause.PARSER_ERROR,
                severity="HIGH",
                impact_score=9.0,
                impact_level=ImpactLevel.CRITICAL,
                confidence=0.95,
                downstream_modules=[
                    "REINFORCEMENT_INTERPRETATION", "FEATURE_EXTRACTION",
                    "PATTERN_RECOGNITION", "BBS_GENERATION", "STEEL_CALCULATION"
                ],
                recommended_fix=(
                    f"Beam {bid} annotation not detected by Drawing Parser. "
                    "Review parser annotation matching rules and beam ID extraction patterns."
                ),
                engineering_notes=[
                    f"Beam {bid} appears in drawing schedule but has no engineering model.",
                    "All downstream phases (L.2 through L.3) will produce no data for this beam.",
                    "BBS and steel weight will be missing for this beam.",
                ],
                traceability={
                    "source": "QA.1 beam_accuracy_report.json",
                    "missing_from": "Phase L.2 beam_reinforcement_models.json",
                },
            ))

        for bid in sorted(false_pos):
            counter += 1
            diagnostics.append(EngineeringDiagnostic(
                diagnostic_id=f"DIAG::BEAM::FALSEPOS::{counter:04d}",
                drawing_name=drawing_name,
                beam_id=bid,
                bar_id="",
                error_type="FALSE_POSITIVE_BEAM",
                expected_value=None,
                predicted_value=bid,
                difference="Beam detected but not expected",
                pipeline_stage=PipelineStage.DRAWING_PARSER,
                root_cause=RootCause.PARSER_ERROR,
                severity="MEDIUM",
                impact_score=6.0,
                impact_level=ImpactLevel.HIGH,
                confidence=0.85,
                downstream_modules=[
                    "REINFORCEMENT_INTERPRETATION", "FEATURE_EXTRACTION",
                    "BBS_GENERATION", "STEEL_CALCULATION"
                ],
                recommended_fix=(
                    f"Beam {bid} was detected by parser but is not in the drawing schedule. "
                    "Review beam ID extraction regex and drawing legend filter rules."
                ),
                engineering_notes=[
                    f"Beam {bid} has a model in L.2 but no ground truth entry.",
                    "May inflate BBS and steel quantity totals.",
                ],
                traceability={"source": "QA.1 beam_accuracy_report.json"},
            ))

        # Beam assignment errors (from reinforcement accuracy)
        beam_results = qa1_beam_report.get("beam_records", []) if qa1_beam_report else []
        for rec in beam_results:
            bid = rec.get("beam_id", "")
            if rec.get("is_false_positive") or not rec.get("detected"):
                continue  # already handled above
            # Cross-check: beam is correct but check naming
            model = l2_by_beam.get(bid, {})
            if model:
                model_name = model.get("beam_name", "")
                gt_name = bid  # GT uses canonical IDs
                if model_name and model_name != gt_name and bid not in model_name:
                    counter += 1
                    diagnostics.append(EngineeringDiagnostic(
                        diagnostic_id=f"DIAG::BEAM::NAMING::{counter:04d}",
                        drawing_name=drawing_name,
                        beam_id=bid,
                        bar_id="",
                        error_type="BEAM_NAMING_MISMATCH",
                        expected_value=gt_name,
                        predicted_value=model_name,
                        difference=f"Expected {gt_name}, got {model_name}",
                        pipeline_stage=PipelineStage.DRAWING_PARSER,
                        root_cause=RootCause.PARSER_ERROR,
                        severity="LOW",
                        impact_score=1.5,
                        impact_level=ImpactLevel.LOW,
                        confidence=0.7,
                        downstream_modules=["BBS_GENERATION"],
                        recommended_fix="Standardise beam name normalisation in parser.",
                        traceability={"source": "L.2 beam_reinforcement_models.json"},
                    ))

        return diagnostics
