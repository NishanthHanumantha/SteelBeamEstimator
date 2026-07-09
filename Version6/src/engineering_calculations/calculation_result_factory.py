"""Calculation result factory — Phase I.2.2."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.engineering_calculations.calculation_result_builder import CalculationResultBuilder
from src.engineering_calculations.calculation_result_registry import CalculationResultRegistry
from src.engineering_calculations.calculation_result_types import CalculationType


class CalculationResultFactory:
    """Canonical factory for future engineering calculation engines."""

    def __init__(self) -> None:
        self._builder = CalculationResultBuilder()
        self._registry = CalculationResultRegistry()

    @property
    def registry(self) -> CalculationResultRegistry:
        return self._registry

    def create_result(
        self,
        calculation_type: CalculationType,
        context: dict[str, Any],
        bar: dict[str, Any],
        readiness: dict[str, Any],
        group: Optional[dict[str, Any]] = None,
        register: bool = True,
        calculation_inputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a framework calculation result for a single bar and calculation type."""
        result = self._builder.build(
            context,
            bar,
            readiness,
            calculation_type,
            group=group,
            registry=self._registry,
            calculation_inputs=calculation_inputs,
        )
        if register:
            self._registry.register(result)
        return result

    def initialize_framework(
        self,
        bars: List[dict[str, Any]],
        groups: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]] | None = None,
        project_id: str = "",
    ) -> Tuple[List[dict[str, Any]], dict[str, Any]]:
        """Initialize framework results for all bars and supported calculation types."""
        results, registry = self._builder.build_framework_results(bars, groups, contexts)
        for bar_id in sorted({str(bar.get("bar_id", "")) for bar in bars if bar.get("bar_id")}):
            registry.mark_processed(bar_id)

        exports = CalculationResultBuilder.build_project_exports(
            results,
            registry,
            bars,
            drawing_models or [],
            project_id=project_id,
        )
        return results, exports
