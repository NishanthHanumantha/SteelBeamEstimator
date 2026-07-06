"""Geometry length correspondence analysis — Phase QA.2."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.estimator_validation.audit_types import FLOAT_TOLERANCE
from src.estimator_validation.comparison_utils import BeamBlock, to_float
from src.estimator_validation.object_trace.trace_types import TraceRootCause


LENGTH_FIELDS: tuple[tuple[str, str], ...] = (
    ("clear_span_mm", "Clear Span"),
    ("effective_span_mm", "Effective Span"),
    ("beam_length_mm", "Overall Beam Length"),
    ("center_to_center_span_mm", "Center-to-Center Span"),
    ("support_to_support_span_mm", "Support-to-Support Length"),
    ("dimension_chain_length_mm", "Dimension Chain Length"),
    ("overall_beam_length_mm", "Overall Beam Length"),
    ("span_mm", "Span"),
)


class GeometryComparator:
    """Determine which stored engineering length best matches estimator clear span."""

    def compare_beams(
        self,
        estimator_beams: Dict[str, BeamBlock],
        generated_beams: Dict[str, BeamBlock],
        beam_summaries: Dict[str, dict[str, Any]],
        engineering_reports: Dict[str, dict[str, Any]],
        calculation_contexts: List[dict[str, Any]],
        framing_beams: List[dict[str, Any]],
        geometry_beams: List[dict[str, Any]],
    ) -> dict[str, Any]:
        beams: List[dict[str, Any]] = []
        for beam_mark, block in sorted(estimator_beams.items(), key=lambda item: int(item[0][1:])):
            estimator_m = block.clear_span_m
            if estimator_m is None:
                continue
            generated_block = generated_beams.get(beam_mark)
            generated_m = generated_block.clear_span_m if generated_block else None
            candidates = self._collect_length_candidates(
                beam_mark,
                beam_summaries.get(beam_mark),
                engineering_reports.get(beam_mark),
                calculation_contexts,
                framing_beams,
                geometry_beams,
            )
            comparisons = []
            best_match = None
            best_delta = None
            for field_key, label, value_mm in candidates:
                value_m = value_mm / 1000.0
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
                    best_match = entry
            conclusion = "No correspondence found"
            root_cause = TraceRootCause.UNKNOWN.value
            if best_match and best_match["within_tolerance"]:
                conclusion = f"Estimator uses {best_match['label']}"
                root_cause = TraceRootCause.GEOMETRY.value
            elif best_match:
                conclusion = (
                    f"Closest correspondence: {best_match['label']} "
                    f"(delta {best_match['difference_m']:.3f} m)"
                )
                root_cause = TraceRootCause.GEOMETRY.value
            beams.append(
                {
                    "beam_mark": beam_mark,
                    "estimator_clear_span_m": estimator_m,
                    "generated_clear_span_m": generated_m,
                    "comparisons": comparisons,
                    "best_match": best_match,
                    "conclusion": conclusion,
                    "root_cause_hint": root_cause,
                }
            )
        return {
            "phase": "Phase QA.2",
            "beam_count": len(beams),
            "beams": beams,
            "status": "COMPLETE",
        }

    def _collect_length_candidates(
        self,
        beam_mark: str,
        summary: Optional[dict[str, Any]],
        report: Optional[dict[str, Any]],
        contexts: List[dict[str, Any]],
        framing: List[dict[str, Any]],
        geometry: List[dict[str, Any]],
    ) -> List[tuple[str, str, float]]:
        candidates: List[tuple[str, str, float]] = []
        seen: set[tuple[str, float]] = set()

        def add(source: dict[str, Any], prefix: str = "") -> None:
            for field_key, label in LENGTH_FIELDS:
                value = source.get(field_key)
                if value is None:
                    continue
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    continue
                key = (field_key, numeric)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append((f"{prefix}{field_key}" if prefix else field_key, label, numeric))

        if summary:
            add(summary, "beam_summary.")
        if report:
            header = report.get("sections", {}).get("header", {})
            add(header, "engineering_report.")
        for ctx in contexts:
            if str(ctx.get("beam_id")) != beam_mark:
                continue
            add(ctx, "calculation_context.")
        for item in framing:
            if str(item.get("beam_mark") or item.get("beam_id")) != beam_mark:
                continue
            add(item, "framing.")
        for item in geometry:
            mark = str(item.get("beam_mark") or item.get("beam_id") or "")
            if mark != beam_mark and beam_mark not in str(item):
                continue
            add(item, "geometry.")

        return candidates
