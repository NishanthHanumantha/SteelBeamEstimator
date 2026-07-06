"""Interpretation trace for estimator reinforcement rows — Phase QA.3."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.estimator_validation.comparison_utils import beam_sort_key
from src.estimator_validation.drawing_interpretation.interpretation_types import (
    BeamInterpretation,
    InterpretationRootCause,
)


class InterpretationTraceBuilder:
    """Trace drawing → estimator → pipeline for each estimator concept."""

    def build(
        self,
        estimator: Dict[str, BeamInterpretation],
        drawing: Dict[str, BeamInterpretation],
        pipeline: Dict[str, BeamInterpretation],
        matching: dict[str, Any],
    ) -> dict[str, Any]:
        match_index = {
            (entry["beam_mark"], entry["concept_key"]): entry for entry in matching.get("entries", [])
        }
        traces: List[dict[str, Any]] = []
        for beam_mark in sorted(estimator.keys(), key=beam_sort_key):
            est_interp = estimator[beam_mark]
            for concept in est_interp.concepts:
                key = concept.concept_key()
                match = match_index.get((beam_mark, key))
                if match is None:
                    relaxed = self._find_relaxed_match(beam_mark, concept.role, concept.diameter_mm, match_index)
                    match = relaxed
                drawing_status = "PASS" if match and match.get("in_drawing") else "FAIL"
                estimator_status = "PASS"
                pipeline_status = "PASS" if match and match.get("in_pipeline") else "FAIL"
                conclusion = self._conclusion(drawing_status, estimator_status, pipeline_status, concept.role)
                traces.append(
                    {
                        "beam_mark": beam_mark,
                        "concept": concept.to_dict(),
                        "drawing": {"status": drawing_status, "present": match.get("in_drawing") if match else False},
                        "estimator": {"status": estimator_status, "present": True},
                        "pipeline": {"status": pipeline_status, "present": match.get("in_pipeline") if match else False},
                        "classification": match.get("classification") if match else "UNKNOWN",
                        "root_cause": match.get("root_cause") if match else InterpretationRootCause.UNKNOWN.value,
                        "confidence": match.get("confidence", 0) if match else 0,
                        "conclusion": conclusion,
                    }
                )
        return {"trace_count": len(traces), "traces": traces}

    @staticmethod
    def _find_relaxed_match(
        beam_mark: str,
        role: str,
        diameter: Optional[float],
        match_index: dict[tuple[str, str], dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        prefix = f"{beam_mark}|{role}|"
        for (mark, key), entry in match_index.items():
            if mark != beam_mark:
                continue
            if key.startswith(prefix):
                if diameter is None or str(int(diameter)) in key:
                    return entry
        return None

    @staticmethod
    def _conclusion(drawing: str, estimator: str, pipeline: str, role: str) -> str:
        if drawing == "PASS" and estimator == "PASS" and pipeline == "PASS":
            return "Correct interpretation across all sources."
        if drawing == "PASS" and estimator == "PASS" and pipeline == "FAIL":
            return "Pipeline under-interpreted drawing."
        if drawing == "FAIL" and estimator == "PASS" and pipeline == "FAIL":
            if role in {"SPACER_BAR", "SFR"}:
                return "Estimator manual interpretation."
            return "Estimator engineering decision beyond explicit drawing callouts."
        if drawing == "PASS" and pipeline == "PASS" and estimator == "PASS":
            return "Correct interpretation."
        if drawing == "PASS" and pipeline == "PASS":
            return "Drawing and pipeline aligned."
        if estimator == "PASS" and pipeline == "FAIL":
            return "Pipeline missing estimator interpretation."
        return "Interpretation mismatch requires engineering review."
