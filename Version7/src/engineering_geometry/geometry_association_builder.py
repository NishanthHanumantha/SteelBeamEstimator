"""Geometry Association Builder — Phase H.2."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.engineering_geometry.geometry_association import build_engineering_geometry_association
from src.engineering_geometry.geometry_reference import (
    format_beam_geometry_id,
    format_beam_section_id,
    format_clear_span_id,
    format_coordinate_system_id,
    format_effective_span_id,
    format_knowledge_graph_node_id,
    format_stationing_id,
    format_support_end_id,
    format_support_start_id,
    resolve_support_reference_id,
)
from src.engineering_geometry.geometry_registry import GeometryAssociationRegistry
from src.engineering_geometry.geometry_types import (
    REFERENCE_CONTRACT_VERSION,
    STATUS_AMBIGUOUS,
    STATUS_INVALID_REFERENCE,
    STATUS_MISSING_BEAM,
    STATUS_MISSING_GEOMETRY,
    STATUS_UNRESOLVED,
    STATUS_VALID,
)
from src.engineering_geometry.phase_f_registry_index import PhaseFRegistryIndex
from src.engineering_specifications.specification_types import STATUS_DEFERRED


class GeometryAssociationBuilder:
    """Link engineering specifications to Phase F geometry through immutable IDs."""

    def build(
        self,
        specifications: List[dict[str, Any]],
        model: dict[str, Any],
    ) -> Tuple[List[dict[str, Any]], GeometryAssociationRegistry]:
        index = PhaseFRegistryIndex(model)
        registry = GeometryAssociationRegistry()
        associations: List[dict[str, Any]] = []

        sorted_specs = sorted(
            specifications,
            key=lambda item: str(item.get("specification_id", "")),
        )

        for spec in sorted_specs:
            registry.mark_processed(str(spec.get("specification_id", "")))
            association = self._associate_specification(spec, index, registry, model)
            registry.register(association)
            associations.append(association)

        return associations, registry

    @staticmethod
    def build_project_exports(
        associations: List[dict[str, Any]],
        registry: GeometryAssociationRegistry,
        specifications: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]],
        project_id: str = "",
    ) -> dict[str, Any]:
        primary = drawing_models[0] if drawing_models else {}
        geometry_registry = GeometryAssociationRegistry.build_project_registry(
            associations,
            specifications,
            registry.processed_specification_ids,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )
        return {
            "geometry_associations": associations,
            "geometry_registry": geometry_registry,
        }

    def _associate_specification(
        self,
        spec: dict[str, Any],
        index: PhaseFRegistryIndex,
        registry: GeometryAssociationRegistry,
        model: dict[str, Any],
    ) -> dict[str, Any]:
        specification_id = str(spec.get("specification_id", ""))
        engineering_object_id = str(spec.get("engineering_object_id", ""))
        beam_mark = str(spec.get("beam_id", "")).strip()

        if not beam_mark:
            return build_engineering_geometry_association(
                association_id=registry.next_id(),
                specification_id=specification_id,
                engineering_object_id=engineering_object_id,
                beam_id="",
                beam_geometry_id="",
                beam_section_id="",
                clear_span_id="",
                effective_span_id="",
                stationing_id="",
                coordinate_system_id="",
                support_start_id="",
                support_end_id="",
                knowledge_graph_node_id="",
                association_status=STATUS_MISSING_BEAM,
                association_reason="Specification has no beam_id.",
                association_confidence=0.0,
                traceability=self._build_traceability(spec, model, None, {}),
                reference_contract_version=REFERENCE_CONTRACT_VERSION,
            )

        if str(spec.get("specification_status", "")) == STATUS_DEFERRED:
            return self._build_deferred_association(
                spec, index, registry, model, beam_mark, STATUS_UNRESOLVED,
                "Specification deferred; geometry association unresolved.",
            )

        beam_records = [
            mark
            for mark in index.beam_marks
            if mark == beam_mark
        ]
        graph_nodes = [
            node
            for mark, node in [(beam_mark, index.graph_beam_node(beam_mark))]
            if node
        ]

        if len(beam_records) > 1 or len(graph_nodes) > 1:
            return self._build_deferred_association(
                spec, index, registry, model, beam_mark, STATUS_AMBIGUOUS,
                "Multiple geometry candidates found for beam.",
            )

        if not index.has_beam_mark(beam_mark):
            return build_engineering_geometry_association(
                association_id=registry.next_id(),
                specification_id=specification_id,
                engineering_object_id=engineering_object_id,
                beam_id=beam_mark,
                beam_geometry_id="",
                beam_section_id="",
                clear_span_id="",
                effective_span_id="",
                stationing_id="",
                coordinate_system_id="",
                support_start_id="",
                support_end_id="",
                knowledge_graph_node_id="",
                association_status=STATUS_MISSING_GEOMETRY,
                association_reason=f"No Phase F geometry found for beam {beam_mark}.",
                association_confidence=0.0,
                traceability=self._build_traceability(spec, model, None, {}),
                reference_contract_version=REFERENCE_CONTRACT_VERSION,
            )

        beam = index.beam_record(beam_mark) or {}
        refs = self._resolve_references(beam_mark, beam, index)
        status, reason, confidence = self._determine_status(beam_mark, refs, index)

        return build_engineering_geometry_association(
            association_id=registry.next_id(),
            specification_id=specification_id,
            engineering_object_id=engineering_object_id,
            beam_id=beam_mark,
            beam_geometry_id=refs["beam_geometry_id"],
            beam_section_id=refs["beam_section_id"],
            clear_span_id=refs["clear_span_id"],
            effective_span_id=refs["effective_span_id"],
            stationing_id=refs["stationing_id"],
            coordinate_system_id=refs["coordinate_system_id"],
            support_start_id=refs["support_start_id"],
            support_end_id=refs["support_end_id"],
            knowledge_graph_node_id=refs["knowledge_graph_node_id"],
            association_status=status,
            association_reason=reason,
            association_confidence=confidence,
            traceability=self._build_traceability(spec, model, beam, refs),
            reference_contract_version=REFERENCE_CONTRACT_VERSION,
        )

    def _build_deferred_association(
        self,
        spec: dict[str, Any],
        index: PhaseFRegistryIndex,
        registry: GeometryAssociationRegistry,
        model: dict[str, Any],
        beam_mark: str,
        status: str,
        reason: str,
    ) -> dict[str, Any]:
        refs = self._resolve_references(
            beam_mark,
            index.beam_record(beam_mark) or {},
            index,
        )
        return build_engineering_geometry_association(
            association_id=registry.next_id(),
            specification_id=str(spec.get("specification_id", "")),
            engineering_object_id=str(spec.get("engineering_object_id", "")),
            beam_id=beam_mark,
            beam_geometry_id=refs["beam_geometry_id"],
            beam_section_id=refs["beam_section_id"],
            clear_span_id=refs["clear_span_id"],
            effective_span_id=refs["effective_span_id"],
            stationing_id=refs["stationing_id"],
            coordinate_system_id=refs["coordinate_system_id"],
            support_start_id=refs["support_start_id"],
            support_end_id=refs["support_end_id"],
            knowledge_graph_node_id=refs["knowledge_graph_node_id"],
            association_status=status,
            association_reason=reason,
            association_confidence=0.0,
            traceability=self._build_traceability(
                spec,
                model,
                index.beam_record(beam_mark),
                refs,
            ),
            reference_contract_version=REFERENCE_CONTRACT_VERSION,
        )

    @staticmethod
    def _resolve_references(
        beam_mark: str,
        beam: dict[str, Any],
        index: PhaseFRegistryIndex,
    ) -> Dict[str, str]:
        engineering_refs = beam.get("engineering_references", {})
        supports = beam.get("supports", {})
        left = supports.get("left", {}) if isinstance(supports, dict) else {}
        right = supports.get("right", {}) if isinstance(supports, dict) else {}

        section_ref = str(
            engineering_refs.get("section_id")
            or format_beam_section_id(beam_mark)
        )
        ecs_ref = str(
            engineering_refs.get("coordinate_system_id")
            or format_coordinate_system_id(beam_mark)
        )

        return {
            "beam_geometry_id": format_beam_geometry_id(beam_mark),
            "beam_section_id": section_ref,
            "clear_span_id": format_clear_span_id(beam_mark),
            "effective_span_id": format_effective_span_id(beam_mark),
            "stationing_id": format_stationing_id(beam_mark),
            "coordinate_system_id": ecs_ref,
            "support_start_id": resolve_support_reference_id(
                str(left.get("type", "")),
                left.get("id"),
                format_support_start_id(beam_mark),
            ),
            "support_end_id": resolve_support_reference_id(
                str(right.get("type", "")),
                right.get("id"),
                format_support_end_id(beam_mark),
            ),
            "knowledge_graph_node_id": format_knowledge_graph_node_id(beam_mark),
        }

    @staticmethod
    def _determine_status(
        beam_mark: str,
        refs: Dict[str, str],
        index: PhaseFRegistryIndex,
    ) -> Tuple[str, str, float]:
        checks = [
            ("beam_geometry_id", "beam_geometry"),
            ("beam_section_id", "section"),
            ("clear_span_id", "clear_span"),
            ("effective_span_id", "effective_span"),
            ("stationing_id", "stationing"),
            ("coordinate_system_id", "coordinate_system"),
            ("knowledge_graph_node_id", "knowledge_graph"),
        ]
        invalid = [
            field
            for field, category in checks
            if not index.validate_reference(refs[field], category, beam_mark)
        ]
        if invalid:
            return (
                STATUS_INVALID_REFERENCE,
                f"Broken registry references: {', '.join(invalid)}",
                0.0,
            )

        beam = index.beam_record(beam_mark) or {}
        confidence = float(
            beam.get("geometry", {}).get("confidence", 0.0)
            or beam.get("length_model", {}).get("confidence", 0.0)
            or 0.85
        )
        return STATUS_VALID, "Single deterministic geometry chain resolved.", confidence

    @staticmethod
    def _build_traceability(
        spec: dict[str, Any],
        model: dict[str, Any],
        beam: dict[str, Any] | None,
        refs: Dict[str, str],
    ) -> dict[str, Any]:
        spec_trace = spec.get("traceability", {})
        beam_refs = (beam or {}).get("engineering_references", {})
        return {
            "lineage": [
                "Geometry Association",
                "Engineering Specification",
                "Engineering Object",
                "Resolved Property",
                "Engineering Property",
                "Property Candidate",
                "Semantic Role",
                "Drawing Entity",
                "Beam Geometry",
                "Knowledge Graph Node",
            ],
            "specification_id": spec.get("specification_id"),
            "engineering_object_id": spec.get("engineering_object_id"),
            "specification_traceability": spec_trace,
            "beam_geometry_reference": refs,
            "phase_f_engineering_references": {
                key: beam_refs.get(key)
                for key in (
                    "section_id",
                    "length_model_id",
                    "coordinate_system_id",
                    "context_id",
                    "support_model_id",
                )
            },
            "knowledge_graph_node_id": refs.get("knowledge_graph_node_id", ""),
            "reference_contract_version": REFERENCE_CONTRACT_VERSION,
        }
