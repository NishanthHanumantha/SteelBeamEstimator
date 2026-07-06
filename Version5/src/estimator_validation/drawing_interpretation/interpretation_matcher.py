"""Compare drawing, estimator, and pipeline engineering concepts — Phase QA.3."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.estimator_validation.audit_types import FLOAT_TOLERANCE
from src.estimator_validation.drawing_interpretation.interpretation_types import (
    BeamInterpretation,
    EngineeringConcept,
    InterpretationClassification,
    InterpretationRootCause,
)


class InterpretationMatcher:
    """Match engineering concepts across drawing, estimator, and pipeline."""

    MANUAL_DECISION_ROLES = frozenset({"SPACER_BAR", "SFR"})

    def match_beams(
        self,
        drawing: Dict[str, BeamInterpretation],
        estimator: Dict[str, BeamInterpretation],
        pipeline: Dict[str, BeamInterpretation],
    ) -> dict[str, Any]:
        entries: List[dict[str, Any]] = []
        classification_counts: Dict[str, int] = {}
        root_cause_counts: Dict[str, int] = {}
        for beam_mark in sorted(set(drawing) | set(estimator) | set(pipeline)):
            drawing_concepts = self._concept_index(drawing.get(beam_mark))
            estimator_concepts = self._concept_index(estimator.get(beam_mark))
            pipeline_concepts = self._concept_index(pipeline.get(beam_mark))
            all_keys = set(drawing_concepts) | set(estimator_concepts) | set(pipeline_concepts)
            for key in sorted(all_keys):
                in_drawing = key in drawing_concepts
                in_estimator = key in estimator_concepts
                in_pipeline = key in pipeline_concepts
                classification = self._classify(in_drawing, in_estimator, in_pipeline)
                root_cause = self._root_cause(
                    classification,
                    drawing_concepts.get(key),
                    estimator_concepts.get(key),
                    pipeline_concepts.get(key),
                )
                classification_counts[classification.value] = classification_counts.get(classification.value, 0) + 1
                root_cause_counts[root_cause.value] = root_cause_counts.get(root_cause.value, 0) + 1
                entries.append(
                    {
                        "beam_mark": beam_mark,
                        "concept_key": key,
                        "drawing": drawing_concepts.get(key).to_dict() if in_drawing else None,
                        "estimator": estimator_concepts.get(key).to_dict() if in_estimator else None,
                        "pipeline": pipeline_concepts.get(key).to_dict() if in_pipeline else None,
                        "in_drawing": in_drawing,
                        "in_estimator": in_estimator,
                        "in_pipeline": in_pipeline,
                        "classification": classification.value,
                        "root_cause": root_cause.value,
                        "confidence": self._confidence(in_drawing, in_estimator, in_pipeline),
                    }
                )
        return {
            "entry_count": len(entries),
            "entries": entries,
            "classification_distribution": classification_counts,
            "root_cause_distribution": root_cause_counts,
        }

    def detect_engineering_decisions(
        self,
        matching: dict[str, Any],
        drawing: Dict[str, BeamInterpretation],
    ) -> dict[str, Any]:
        decisions: List[dict[str, Any]] = []
        drawing_roles_by_beam = {
            beam_mark: {concept.role for concept in interp.concepts}
            for beam_mark, interp in drawing.items()
        }
        drawing_callouts_by_beam = {
            beam_mark: set(interp.raw_annotations)
            for beam_mark, interp in drawing.items()
        }
        for entry in matching.get("entries", []):
            if entry.get("classification") != InterpretationClassification.ESTIMATOR_ONLY.value:
                continue
            estimator = entry.get("estimator") or {}
            role = estimator.get("role")
            beam_mark = entry.get("beam_mark")
            decision_type = "Estimator Engineering Decision"
            if role in self.MANUAL_DECISION_ROLES:
                decision_type = "Manual Spacer/SFR"
            elif role in drawing_roles_by_beam.get(beam_mark, set()):
                decision_type = "Engineering Interpretation"
            elif not self._callout_supports(drawing_callouts_by_beam.get(beam_mark, set()), estimator):
                decision_type = "Manual Estimator Adjustment"
            decisions.append(
                {
                    "beam_mark": beam_mark,
                    "concept_key": entry.get("concept_key"),
                    "role": role,
                    "description": estimator.get("description"),
                    "diameter_mm": estimator.get("diameter_mm"),
                    "decision_type": decision_type,
                    "classification": entry.get("classification"),
                    "root_cause": InterpretationRootCause.ESTIMATOR_ENGINEERING_DECISION.value,
                    "confidence": entry.get("confidence"),
                }
            )
        return {
            "decision_count": len(decisions),
            "decisions": decisions,
        }

    def build_engineering_concepts(self, matching: dict[str, Any]) -> dict[str, Any]:
        return {
            "concept_count": matching.get("entry_count", 0),
            "classification_distribution": matching.get("classification_distribution", {}),
            "concepts": matching.get("entries", []),
        }

    @staticmethod
    def _concept_index(interpretation: Optional[BeamInterpretation]) -> Dict[str, EngineeringConcept]:
        if interpretation is None:
            return {}
        indexed: Dict[str, EngineeringConcept] = {}
        for concept in interpretation.concepts:
            key = f"{concept.beam_mark}|{concept.role}|{concept.diameter_mm or ''}"
            if key not in indexed:
                indexed[key] = concept
            strict = concept.concept_key()
            indexed[strict] = concept
        return indexed

    @staticmethod
    def _classify(in_drawing: bool, in_estimator: bool, in_pipeline: bool) -> InterpretationClassification:
        if in_drawing and in_estimator and in_pipeline:
            return InterpretationClassification.DRAWING_AND_ESTIMATOR_AND_PIPELINE
        if in_drawing and in_estimator:
            return InterpretationClassification.DRAWING_AND_ESTIMATOR_ONLY
        if in_drawing and in_pipeline:
            return InterpretationClassification.DRAWING_AND_PIPELINE_ONLY
        if in_estimator and in_pipeline and not in_drawing:
            return InterpretationClassification.DRAWING_AND_ESTIMATOR_AND_PIPELINE
        if in_estimator:
            return InterpretationClassification.ESTIMATOR_ONLY
        if in_pipeline:
            return InterpretationClassification.PIPELINE_ONLY
        if in_drawing:
            return InterpretationClassification.DRAWING_ONLY
        return InterpretationClassification.UNKNOWN

    @staticmethod
    def _root_cause(
        classification: InterpretationClassification,
        drawing: Optional[EngineeringConcept],
        estimator: Optional[EngineeringConcept],
        pipeline: Optional[EngineeringConcept],
    ) -> InterpretationRootCause:
        if classification == InterpretationClassification.ESTIMATOR_ONLY:
            if estimator and estimator.role in InterpretationMatcher.MANUAL_DECISION_ROLES:
                return InterpretationRootCause.ESTIMATOR_ENGINEERING_DECISION
            return InterpretationRootCause.ESTIMATOR_ENGINEERING_DECISION
        if classification == InterpretationClassification.PIPELINE_ONLY:
            return InterpretationRootCause.PARSER_INTERPRETATION
        if classification == InterpretationClassification.DRAWING_ONLY:
            return InterpretationRootCause.PARSER_INTERPRETATION
        if classification == InterpretationClassification.DRAWING_AND_ESTIMATOR_ONLY:
            return InterpretationRootCause.IDENTITY
        if classification == InterpretationClassification.DRAWING_AND_PIPELINE_ONLY:
            return InterpretationRootCause.ENGINEERING_INTERPRETATION
        if classification == InterpretationClassification.DRAWING_AND_ESTIMATOR_AND_PIPELINE:
            return InterpretationRootCause.ENGINEERING_INTERPRETATION
        if drawing is None and estimator and pipeline:
            return InterpretationRootCause.BEAM_SCHEDULE
        return InterpretationRootCause.UNKNOWN

    @staticmethod
    def _confidence(in_drawing: bool, in_estimator: bool, in_pipeline: bool) -> int:
        count = sum([in_drawing, in_estimator, in_pipeline])
        if count == 3:
            return 100
        if count == 2:
            return 85
        if count == 1:
            return 60
        return 0

    @staticmethod
    def _callout_supports(callouts: set[str], estimator: dict[str, Any]) -> bool:
        role = str(estimator.get("role") or "")
        diameter = estimator.get("diameter_mm")
        for callout in callouts:
            upper = callout.upper()
            if role.replace("_", " ")[:3] in upper:
                return True
            if diameter is not None and str(int(diameter)) in upper.replace("Y", ""):
                return True
        return False

    def build_root_cause_matrix(self, matching: dict[str, Any]) -> dict[str, Any]:
        matrix: Dict[str, Dict[str, int]] = {}
        unknown = 0
        for entry in matching.get("entries", []):
            classification = entry.get("classification", "UNKNOWN")
            root_cause = entry.get("root_cause", "Unknown")
            matrix.setdefault(classification, {})
            matrix[classification][root_cause] = matrix[classification].get(root_cause, 0) + 1
            if root_cause == InterpretationRootCause.UNKNOWN.value:
                unknown += 1
        total = max(matching.get("entry_count", 1), 1)
        return {
            "matrix": matrix,
            "unknown_count": unknown,
            "unknown_pct": round(100.0 * unknown / total, 2),
        }

    def build_length_interpretation(
        self,
        data: dict[str, Any],
        generated_workbook_path: Path,
        estimator_workbook_path: Path,
    ) -> dict[str, Any]:
        from src.estimator_validation.comparison_utils import (
            find_schedule_start_row,
            load_workbook_pair,
            parse_schedule_rows,
        )

        _, _, gen_ws, est_ws = load_workbook_pair(generated_workbook_path, estimator_workbook_path)
        est_beams = parse_schedule_rows(est_ws, find_schedule_start_row(est_ws))
        gen_beams = parse_schedule_rows(gen_ws, find_schedule_start_row(gen_ws))

        beams_report: List[dict[str, Any]] = []
        clear_span_index = {
            str(item.get("beam_mark") or item.get("beam_id")): item for item in data.get("clear_spans", [])
        }
        for beam_mark, est_block in sorted(est_beams.items(), key=lambda item: int(item[0][1:])):
            estimator_m = est_block.clear_span_m
            generated_m = (gen_beams.get(beam_mark).clear_span_m if gen_beams.get(beam_mark) else None)
            candidates: List[Tuple[str, str, float]] = []
            span_record = clear_span_index.get(beam_mark, {})
            clear_value = ((span_record.get("clear_span") or {}).get("value"))
            if clear_value is not None:
                candidates.append(("clear_spans.clear_span", "Clear Span", float(clear_value) / 1000.0))
            summary = data["summaries_by_beam"].get(beam_mark, {})
            if summary.get("clear_span_mm") is not None:
                candidates.append(("beam_summary.clear_span_mm", "Clear Span", float(summary["clear_span_mm"]) / 1000.0))
            if summary.get("effective_span_mm") is not None:
                candidates.append(
                    ("beam_summary.effective_span_mm", "Effective Span", float(summary["effective_span_mm"]) / 1000.0)
                )
            for ctx in data.get("calculation_contexts", []):
                if str(ctx.get("beam_id")) != beam_mark:
                    continue
                if ctx.get("clear_span_mm") is not None:
                    candidates.append(
                        ("calculation_context.clear_span_mm", "Clear Span", float(ctx["clear_span_mm"]) / 1000.0)
                    )
                if ctx.get("beam_length_mm") is not None:
                    candidates.append(
                        ("calculation_context.beam_length_mm", "Overall Beam Length", float(ctx["beam_length_mm"]) / 1000.0)
                    )
            for dim in data.get("beam_dimensions", []):
                mark = str(dim.get("beam_mark") or dim.get("beam_id") or "")
                if mark != beam_mark:
                    continue
                dimensions = dim.get("dimensions") or dim
                for field_key, label in (
                    ("overall_length_mm", "Overall Beam"),
                    ("center_to_center_mm", "Support Centre Distance"),
                    ("dimension_chain_mm", "Dimension Chain"),
                ):
                    value = dimensions.get(field_key)
                    if value is not None:
                        candidates.append((field_key, label, float(value) / 1000.0))

            comparisons = []
            best = None
            best_delta = None
            for field_key, label, value_m in candidates:
                if estimator_m is None:
                    continue
                delta = abs(estimator_m - value_m)
                entry = {
                    "field": field_key,
                    "label": label,
                    "value_m": round(value_m, 6),
                    "difference_m": round(delta, 6),
                    "within_tolerance": delta <= FLOAT_TOLERANCE,
                }
                comparisons.append(entry)
                if best_delta is None or delta < best_delta:
                    best_delta = delta
                    best = entry

            conclusion = "Unknown"
            if best and best["within_tolerance"]:
                conclusion = best["label"]
            elif best and best_delta is not None and best_delta <= 0.01:
                conclusion = f"Closest: {best['label']}"
            elif estimator_m is not None and generated_m is not None and abs(estimator_m - generated_m) <= FLOAT_TOLERANCE:
                conclusion = "Manual Estimator Length"
            elif best:
                conclusion = f"Manual Estimator Length (closest {best['label']} delta {best['difference_m']:.3f} m)"

            beams_report.append(
                {
                    "beam_mark": beam_mark,
                    "estimator_l_spcg_m": estimator_m,
                    "generated_clear_span_m": generated_m,
                    "comparisons": comparisons,
                    "best_match": best,
                    "conclusion": conclusion,
                }
            )
        return {
            "phase": "Phase QA.3",
            "beam_count": len(beams_report),
            "beams": beams_report,
            "status": "COMPLETE",
        }
