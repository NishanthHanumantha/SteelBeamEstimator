"""
Phase QA.1.1 — Module 7: Pattern Error Diagnostics
Analyse span/continuity/support/structural behaviour/top-bottom balance/dominant rein.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

from typing import Any, Dict, List

from diagnostic_models import (
    EngineeringDiagnostic, ImpactLevel, PipelineStage, RootCause
)


class PatternErrorDiagnostics:
    """Diagnoses pattern-level errors from QA.1 pattern accuracy."""

    def diagnose(
        self,
        qa1_summary: Dict[str, Any],
        qa1_pattern_report: Dict[str, Any],
        l3_by_beam: Dict[str, Any],
        ground_truth: Dict[str, Any],
        drawing_name: str,
    ) -> List[EngineeringDiagnostic]:
        diagnostics: List[EngineeringDiagnostic] = []
        counter = 0

        pattern_acc = qa1_summary.get("pattern_accuracy", 100.0) or 100.0

        if pattern_acc >= 100.0:
            # All patterns correct — record a pass diagnostic
            counter += 1
            diagnostics.append(EngineeringDiagnostic(
                diagnostic_id=f"DIAG::PATTERN::PASS::{counter:04d}",
                drawing_name=drawing_name,
                beam_id="ALL",
                bar_id="",
                error_type="KPI_GAP_PATTERN",
                expected_value="100.0%",
                predicted_value="100.0%",
                difference="No gap — pattern recognition is perfect",
                pipeline_stage=PipelineStage.PATTERN_RECOGNITION,
                root_cause=RootCause.UNKNOWN,
                severity="LOW",
                impact_score=0.0,
                impact_level=ImpactLevel.LOW,
                confidence=1.0,
                downstream_modules=[],
                recommended_fix=(
                    "Pattern recognition accuracy is 100%. "
                    "No changes required. Monitor for new drawing types."
                ),
                engineering_notes=["Pattern KPI: 100.00% — span, continuity, behaviour all correct."],
                traceability={"source": "QA.1 engineering_accuracy_summary.json"},
            ))
            return diagnostics

        gap = 100.0 - pattern_acc

        # Collect misclassified beams from the L.3 patterns vs ground truth
        gt_patterns = ground_truth.get("patterns", {})
        affected = []
        for bid, pattern in l3_by_beam.items():
            gt_p = gt_patterns.get(bid, {})
            if not gt_p:
                continue
            for attr in ["span_pattern", "continuity_pattern", "structural_behavior"]:
                pred = str(pattern.get(attr, "")).upper()
                exp = str(gt_p.get(attr, "")).upper()
                if pred and exp and pred != exp:
                    affected.append((bid, attr, exp, pred))

        counter += 1
        diagnostics.append(EngineeringDiagnostic(
            diagnostic_id=f"DIAG::PATTERN::KPI_GAP::{counter:04d}",
            drawing_name=drawing_name,
            beam_id="MULTIPLE",
            bar_id="",
            error_type="KPI_GAP_PATTERN",
            expected_value="100.0%",
            predicted_value=f"{pattern_acc:.4f}%",
            difference=f"Gap: {gap:.4f}%",
            pipeline_stage=PipelineStage.PATTERN_RECOGNITION,
            root_cause=RootCause.PATTERN_ERROR,
            severity="HIGH" if gap > 20 else "MEDIUM",
            impact_score=min(8.0, gap * 0.3),
            impact_level=ImpactLevel.HIGH if gap > 20 else ImpactLevel.MEDIUM,
            confidence=0.88,
            downstream_modules=["BBS_GENERATION", "STEEL_CALCULATION"],
            recommended_fix=(
                "Pattern recognition gap detected. "
                "Review span pattern classifier thresholds in Phase L.3. "
                "Check continuity detection logic at beam ends and intermediate supports. "
                "Verify structural behaviour classification against load-path heuristics."
            ),
            engineering_notes=[
                f"Pattern accuracy: {pattern_acc:.2f}% — {gap:.2f}% gap.",
                f"Misclassified attributes: {[a[1] for a in affected]}",
            ],
            traceability={"misclassified": [
                {"beam_id": b, "attribute": a, "expected": e, "predicted": p}
                for b, a, e, p in affected
            ]},
        ))

        for bid, attr, exp, pred in affected:
            counter += 1
            diagnostics.append(EngineeringDiagnostic(
                diagnostic_id=f"DIAG::PATTERN::BEAM::{counter:04d}",
                drawing_name=drawing_name,
                beam_id=bid,
                bar_id="",
                error_type="WRONG_PATTERN",
                expected_value=f"{attr}={exp}",
                predicted_value=f"{attr}={pred}",
                difference=f"Pattern attribute '{attr}' misclassified",
                pipeline_stage=PipelineStage.PATTERN_RECOGNITION,
                root_cause=RootCause.PATTERN_ERROR,
                severity="MEDIUM",
                impact_score=4.0,
                impact_level=ImpactLevel.MEDIUM,
                confidence=0.8,
                downstream_modules=["BBS_GENERATION", "STEEL_CALCULATION"],
                recommended_fix=(
                    f"Beam {bid}: '{attr}' classified as '{pred}' instead of '{exp}'. "
                    "Review the classifier decision boundary for this attribute in L.3."
                ),
                engineering_notes=[f"Beam {bid} {attr}: expected {exp}, got {pred}."],
                traceability={"beam_id": bid, "attribute": attr},
            ))

        return diagnostics
