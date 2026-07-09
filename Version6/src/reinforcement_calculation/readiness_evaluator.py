"""Calculation readiness evaluator — Phase I.2.1."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.calculation_context.calculation_context_types import STATUS_COMPLETE
from src.engineering_geometry.geometry_types import STATUS_VALID
from src.reinforcement_calculation.calculation_readiness import build_calculation_readiness
from src.reinforcement_calculation.calculation_state import CalculationState
from src.reinforcement_calculation.reinforcement_types import STATUS_NORMALIZED


class CalculationReadinessEvaluator:
    """Evaluate whether downstream engineering calculations may proceed."""

    def evaluate(
        self,
        context: dict[str, Any],
        group: dict[str, Any],
        bar: dict[str, Any],
    ) -> dict[str, Any]:
        upstream_summary = self._build_upstream_summary(context, group, bar)
        defer_reasons = self._collect_defer_reasons(context, group, bar, upstream_summary)

        if defer_reasons:
            return build_calculation_readiness(
                CalculationState.DEFERRED,
                defer_reason=defer_reasons[0],
                upstream_status_summary=upstream_summary,
            )

        return build_calculation_readiness(
            CalculationState.READY,
            upstream_status_summary=upstream_summary,
        )

    @staticmethod
    def _build_upstream_summary(
        context: dict[str, Any],
        group: dict[str, Any],
        bar: dict[str, Any],
    ) -> dict[str, Any]:
        context_trace = context.get("traceability", {})
        bar_trace = bar.get("traceability", {})
        return {
            "context_id": context.get("context_id"),
            "context_calculation_status": context.get("calculation_status"),
            "association_status": context_trace.get("association_status"),
            "specification_status": bar_trace.get("specification_status"),
            "reinforcement_bar_status": bar.get("status"),
            "reinforcement_group_status": group.get("status"),
            "quantity": bar.get("quantity"),
            "diameter_mm": bar.get("diameter_mm"),
            "steel_grade": bar.get("steel_grade"),
            "concrete_grade": context.get("concrete_grade"),
            "beam_width_mm": context.get("beam_width_mm"),
            "beam_depth_mm": context.get("beam_depth_mm"),
            "clear_span_mm": context.get("clear_span_mm"),
            "effective_span_mm": context.get("effective_span_mm"),
            "cover_top_mm": context.get("cover_top_mm"),
        }

    @staticmethod
    def _collect_defer_reasons(
        context: dict[str, Any],
        group: dict[str, Any],
        bar: dict[str, Any],
        upstream_summary: dict[str, Any],
    ) -> List[str]:
        reasons: List[str] = []

        if not context or not context.get("context_id"):
            reasons.append("Calculation context missing.")
            return reasons

        context_status = str(context.get("calculation_status", ""))
        if context_status != STATUS_COMPLETE:
            reasons.append("Partial calculation context.")

        association_status = str(
            context.get("traceability", {}).get("association_status", "")
        )
        if association_status and association_status != STATUS_VALID:
            reasons.append("Geometry association unresolved.")

        spec_status = str(bar.get("traceability", {}).get("specification_status", ""))
        if spec_status == "DEFERRED":
            reasons.append("Incomplete reinforcement specification.")

        if str(bar.get("status", "")) != STATUS_NORMALIZED:
            reasons.append("Reinforcement bar not normalized.")

        if str(group.get("status", "")) != STATUS_NORMALIZED:
            reasons.append("Reinforcement group not normalized.")

        quantity = bar.get("quantity")
        if not isinstance(quantity, int) or quantity <= 0:
            reasons.append("Required quantity missing.")

        diameter_mm = bar.get("diameter_mm")
        if not isinstance(diameter_mm, (int, float)) or float(diameter_mm) <= 0:
            reasons.append("Required diameter missing.")

        if not bar.get("steel_grade"):
            reasons.append("Steel grade unresolved.")

        if not context.get("concrete_grade"):
            reasons.append("Concrete grade unresolved.")

        geometry_fields = (
            ("beam_width_mm", "Beam width missing."),
            ("beam_depth_mm", "Beam depth missing."),
            ("clear_span_mm", "Clear span missing."),
            ("effective_span_mm", "Effective span missing."),
        )
        for field, message in geometry_fields:
            value = context.get(field)
            if value is None:
                reasons.append(message)

        if context.get("cover_top_mm") is None:
            reasons.append("Cover unresolved.")

        return reasons
