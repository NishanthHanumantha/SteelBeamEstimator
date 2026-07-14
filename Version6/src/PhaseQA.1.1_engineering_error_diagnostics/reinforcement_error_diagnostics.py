"""
Phase QA.1.1 — Module 4: Reinforcement Error Diagnostics
Analyse wrong beam assignment, bar count, grouping, continuity, support issues.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

from typing import Any, Dict, List

from diagnostic_models import (
    EngineeringDiagnostic, ImpactLevel, PipelineStage, RootCause
)


class ReinforcementErrorDiagnostics:
    """Diagnoses reinforcement-level errors from QA.1 reinforcement accuracy report."""

    def diagnose(
        self,
        qa1_rein_report: Dict[str, Any],
        l2_by_beam: Dict[str, Any],
        ground_truth: Dict[str, Any],
        drawing_name: str,
    ) -> List[EngineeringDiagnostic]:
        diagnostics: List[EngineeringDiagnostic] = []
        counter = 0

        if not qa1_rein_report:
            return diagnostics

        gt_beams = ground_truth.get("reinforcement", {}).get("expected_bars_per_beam", {})

        for beam_result in qa1_rein_report.get("beam_results", []):
            bid = beam_result.get("beam_id", "")
            missing = beam_result.get("missing", 0)
            extra = beam_result.get("extra", 0)
            is_recovered = beam_result.get("recovered", False)

            if is_recovered:
                continue  # Recovered beams have placeholder bars — skip

            gt_entry = gt_beams.get(bid, {})
            model = l2_by_beam.get(bid, {})
            by_role = model.get("bar_count_by_role", {}) if model else {}

            if missing > 0:
                # Determine which roles are missing
                missing_roles = []
                for role in ["TOP_MAIN", "BOTTOM_MAIN", "TOP_EXTRA", "BOTTOM_EXTRA",
                             "STIRRUP", "SIDE_FACE_REINFORCEMENT"]:
                    exp = gt_entry.get(role, 0)
                    det = by_role.get(role, 0)
                    if exp > det:
                        missing_roles.append(f"{role}(exp={exp},det={det})")

                counter += 1
                stage = (PipelineStage.GEOMETRY_RECOVERY if is_recovered
                         else PipelineStage.REINFORCEMENT_INTERPRETATION)
                diagnostics.append(EngineeringDiagnostic(
                    diagnostic_id=f"DIAG::REIN::MISSING::{counter:04d}",
                    drawing_name=drawing_name,
                    beam_id=bid,
                    bar_id="",
                    error_type="MISSING_BARS",
                    expected_value=str(beam_result.get("expected_total")),
                    predicted_value=str(beam_result.get("detected_total")),
                    difference=f"Missing {missing} bars in roles: {missing_roles}",
                    pipeline_stage=stage,
                    root_cause=RootCause.ASSOCIATION_ERROR,
                    severity="HIGH" if missing > 2 else "MEDIUM",
                    impact_score=min(9.0, 3.5 * missing),
                    impact_level=ImpactLevel.HIGH if missing > 1 else ImpactLevel.MEDIUM,
                    confidence=0.9,
                    downstream_modules=[
                        "FEATURE_EXTRACTION", "PATTERN_RECOGNITION",
                        "BBS_GENERATION", "STEEL_CALCULATION"
                    ],
                    recommended_fix=(
                        f"Beam {bid}: {missing} bars not extracted by L.2 interpretation engine. "
                        f"Missing roles: {missing_roles}. "
                        "Review annotation matching rules for low-confidence bars and "
                        "extend the interpretation heuristics for these role types."
                    ),
                    engineering_notes=[
                        f"Beam {bid} has {beam_result.get('expected_total')} expected bars "
                        f"but only {beam_result.get('detected_total')} detected.",
                        f"Missing roles: {missing_roles}",
                        "Downstream BBS and steel weight calculations will be incomplete.",
                    ],
                    traceability={
                        "source": "QA.1 reinforcement_accuracy_report.json",
                        "phase": "L.2",
                    },
                ))

            if extra > 0:
                extra_roles = []
                for role in ["TOP_MAIN", "BOTTOM_MAIN", "TOP_EXTRA", "BOTTOM_EXTRA",
                             "STIRRUP", "SIDE_FACE_REINFORCEMENT"]:
                    exp = gt_entry.get(role, 0)
                    det = by_role.get(role, 0)
                    if det > exp:
                        extra_roles.append(f"{role}(exp={exp},det={det})")

                counter += 1
                diagnostics.append(EngineeringDiagnostic(
                    diagnostic_id=f"DIAG::REIN::EXTRA::{counter:04d}",
                    drawing_name=drawing_name,
                    beam_id=bid,
                    bar_id="",
                    error_type="EXTRA_BARS",
                    expected_value=str(beam_result.get("expected_total")),
                    predicted_value=str(beam_result.get("detected_total")),
                    difference=f"Extra {extra} bars in roles: {extra_roles}",
                    pipeline_stage=PipelineStage.REINFORCEMENT_INTERPRETATION,
                    root_cause=RootCause.ASSOCIATION_ERROR,
                    severity="MEDIUM",
                    impact_score=min(6.0, 2.5 * extra),
                    impact_level=ImpactLevel.MEDIUM,
                    confidence=0.85,
                    downstream_modules=["BBS_GENERATION", "STEEL_CALCULATION"],
                    recommended_fix=(
                        f"Beam {bid}: {extra} extra bars detected. "
                        f"Roles: {extra_roles}. "
                        "Review duplicate bar suppression rules in L.2 interpretation engine."
                    ),
                    engineering_notes=[
                        f"Extra bars in {bid} may inflate steel weight and BBS quantities.",
                    ],
                    traceability={"source": "QA.1 reinforcement_accuracy_report.json"},
                ))

        return diagnostics
