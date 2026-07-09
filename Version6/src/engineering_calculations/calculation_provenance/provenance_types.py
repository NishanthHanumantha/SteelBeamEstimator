"""Calculation provenance type definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

NAMESPACE_CALCULATION_PROVENANCE = "CALCULATION_PROVENANCE"
SOURCE_REFERENCE_SCHEMA_VERSION = "1.0"
PROVENANCE_PHASE = "I.5.A"


@dataclass(frozen=True)
class CalculationSourceReference:
    """Immutable reference to a source EngineeringCalculationResult."""

    result_id: str
    calculation_type: str
    namespace: str
    registry_id: str
    engine_name: str
    engine_version: str
    result_state: str
    value: Any
    unit: str
    timestamp: str
    source_phase: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "calculation_type": self.calculation_type,
            "namespace": self.namespace,
            "registry_id": self.registry_id,
            "engine_name": self.engine_name,
            "engine_version": self.engine_version,
            "result_state": self.result_state,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp,
            "source_phase": self.source_phase,
        }


@dataclass(frozen=True)
class CalculationDependencyReference:
    """Immutable dependency category reference for provenance chains."""

    dependency_category: str
    source_result_id: str
    calculation_type: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "dependency_category": self.dependency_category,
            "source_result_id": self.source_result_id,
            "calculation_type": self.calculation_type,
        }


@dataclass(frozen=True)
class CalculationProvenance:
    """Immutable provenance record for an engineering calculation result."""

    sources: Tuple[CalculationSourceReference, ...]
    dependencies: Tuple[CalculationDependencyReference, ...] = ()
    schema_version: str = SOURCE_REFERENCE_SCHEMA_VERSION
    immutable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "immutable": self.immutable,
            "sources": [source.to_dict() for source in self.sources],
            "dependencies": [dependency.to_dict() for dependency in self.dependencies],
        }

    @property
    def source_count(self) -> int:
        return len(self.sources)
