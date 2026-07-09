"""Calculation provenance builder — reusable provenance construction."""

from __future__ import annotations

from typing import Any, Iterable, List, Optional

from src.engineering_calculations.calculation_provenance.provenance_types import (
    NAMESPACE_CALCULATION_PROVENANCE,
    CalculationDependencyReference,
    CalculationProvenance,
    CalculationSourceReference,
)
from src.engineering_calculations.calculation_result_types import (
    NAMESPACE_CALCULATION_RESULT,
    PREFIX_CALCULATION_RESULT_REGISTRY,
)

DEPENDENCY_CATEGORY_BY_TYPE = {
    "DEVELOPMENT_LENGTH": "DEVELOPMENT_LENGTH",
    "HOOK": "HOOK_LENGTH",
    "LAP_LENGTH": "LAP_LENGTH",
    "CUT_LENGTH": "CUT_LENGTH",
    "BAR_SCHEDULE": "BBS",
    "STEEL_WEIGHT": "STEEL_WEIGHT",
    "BOQ": "BOQ",
}


class CalculationProvenanceBuilder:
    """Build immutable calculation provenance from source EngineeringCalculationResult records."""

    @staticmethod
    def source_reference_from_result(source_result: dict[str, Any]) -> CalculationSourceReference:
        metadata = source_result.get("result_metadata") or {}
        return CalculationSourceReference(
            result_id=str(source_result.get("result_id", "")),
            calculation_type=str(source_result.get("calculation_type", "")),
            namespace=NAMESPACE_CALCULATION_RESULT,
            registry_id=PREFIX_CALCULATION_RESULT_REGISTRY,
            engine_name=str(source_result.get("engine_name", "")),
            engine_version=str(source_result.get("source_engine_version", "")),
            result_state=str(source_result.get("calculation_state", "")),
            value=source_result.get("result_value"),
            unit=str(source_result.get("result_unit", "")),
            timestamp=str(source_result.get("created_timestamp", "")),
            source_phase=str(metadata.get("determination_phase", "")),
        )

    @staticmethod
    def dependency_reference_from_result(
        source_result: dict[str, Any],
    ) -> CalculationDependencyReference:
        calculation_type = str(source_result.get("calculation_type", ""))
        category = DEPENDENCY_CATEGORY_BY_TYPE.get(
            calculation_type,
            calculation_type,
        )
        return CalculationDependencyReference(
            dependency_category=category,
            source_result_id=str(source_result.get("result_id", "")),
            calculation_type=calculation_type,
        )

    @classmethod
    def build_empty(cls) -> dict[str, Any]:
        return CalculationProvenance(sources=(), dependencies=()).to_dict()

    @classmethod
    def build_from_source_results(
        cls,
        source_results: Iterable[dict[str, Any]],
    ) -> dict[str, Any]:
        sources: List[CalculationSourceReference] = []
        dependencies: List[CalculationDependencyReference] = []
        for source_result in source_results:
            if not source_result:
                continue
            sources.append(cls.source_reference_from_result(source_result))
            dependencies.append(cls.dependency_reference_from_result(source_result))
        provenance = CalculationProvenance(
            sources=tuple(sources),
            dependencies=tuple(dependencies),
        )
        return provenance.to_dict()

    @staticmethod
    def attach(result: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
        updated = dict(result)
        updated["calculation_provenance"] = dict(provenance)
        return updated

    @staticmethod
    def provenance_namespace() -> str:
        return NAMESPACE_CALCULATION_PROVENANCE
