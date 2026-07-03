"""Calculation Context Builder — Phase I.1."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.calculation_context.context_loader import CalculationContextLoader
from src.calculation_context.context_models import build_engineering_calculation_context
from src.calculation_context.context_registry import CalculationContextRegistry
from src.calculation_context.calculation_context_types import (
    STATUS_COMPLETE,
    STATUS_INCOMPLETE,
    STATUS_PARTIAL,
)
from src.engineering_geometry.geometry_types import STATUS_VALID
from src.engineering_geometry.phase_f_registry_index import PhaseFRegistryIndex
from src.framing.engineering_ids import length_id, support_beam_id
from src.general_notes.engineering_value import engineering_value_numeric


class CalculationContextBuilder:
    """Assemble immutable engineering calculation contexts from authoritative sources."""

    def __init__(self, rules_path: Path | None = None) -> None:
        self._loader = CalculationContextLoader.from_rules_path(rules_path)

    def build(
        self,
        specifications: List[dict[str, Any]],
        associations: List[dict[str, Any]],
        model: dict[str, Any],
        drawing_models: List[dict[str, Any]] | None = None,
    ) -> Tuple[List[dict[str, Any]], CalculationContextRegistry]:
        index = PhaseFRegistryIndex(model)
        registry = CalculationContextRegistry()
        contexts: List[dict[str, Any]] = []

        association_by_spec = {
            str(item.get("specification_id", "")): item for item in associations
        }
        materials = self._loader.resolve_materials()
        rule_refs = self._loader.resolve_rule_references()
        project_meta = self._project_metadata(model, drawing_models or [])

        sorted_specs = sorted(
            specifications,
            key=lambda item: str(item.get("specification_id", "")),
        )

        for spec in sorted_specs:
            spec_id = str(spec.get("specification_id", ""))
            registry.mark_processed(spec_id)
            association = association_by_spec.get(spec_id, {})
            context = self._build_context(
                spec,
                association,
                index,
                materials,
                rule_refs,
                project_meta,
                model,
                registry,
            )
            registry.register(context)
            contexts.append(context)

        return contexts, registry

    @staticmethod
    def build_project_exports(
        contexts: List[dict[str, Any]],
        registry: CalculationContextRegistry,
        specifications: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]],
        project_id: str = "",
    ) -> dict[str, Any]:
        primary = drawing_models[0] if drawing_models else {}
        calculation_registry = CalculationContextRegistry.build_project_registry(
            contexts,
            specifications,
            registry.processed_specification_ids,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )
        return {
            "calculation_contexts": contexts,
            "calculation_context_registry": calculation_registry,
        }

    def _build_context(
        self,
        spec: dict[str, Any],
        association: dict[str, Any],
        index: PhaseFRegistryIndex,
        materials: dict[str, Any],
        rule_refs: dict[str, dict[str, Any]],
        project_meta: dict[str, str],
        model: dict[str, Any],
        registry: CalculationContextRegistry,
    ) -> dict[str, Any]:
        specification_id = str(spec.get("specification_id", ""))
        association_id = str(association.get("association_id", ""))
        engineering_object_id = str(spec.get("engineering_object_id", ""))
        beam_mark = str(spec.get("beam_id", "") or association.get("beam_id", "")).strip()

        geometry_values = self._resolve_geometry_values(beam_mark, association, index)
        phase_f_refs = self._resolve_phase_f_references(beam_mark, association, index)
        calculation_status = self._resolve_status(association, geometry_values, materials)

        return build_engineering_calculation_context(
            context_id=registry.next_id(),
            specification_id=specification_id,
            association_id=association_id,
            engineering_object_id=engineering_object_id,
            beam_id=beam_mark,
            drawing_id=project_meta.get("drawing_id", ""),
            project_id=project_meta.get("project_id", ""),
            phase="Phase I.1",
            geometry_association_id=association_id,
            beam_geometry_id=str(association.get("beam_geometry_id", phase_f_refs.get("beam_geometry_id", ""))),
            beam_section_id=str(association.get("beam_section_id", phase_f_refs.get("beam_section_id", ""))),
            length_model_id=phase_f_refs.get("length_model_id", ""),
            coordinate_system_id=str(
                association.get("coordinate_system_id", phase_f_refs.get("coordinate_system_id", ""))
            ),
            support_model_id=phase_f_refs.get("support_model_id", ""),
            knowledge_graph_node_id=str(
                association.get("knowledge_graph_node_id", phase_f_refs.get("knowledge_graph_node_id", ""))
            ),
            beam_width_mm=geometry_values.get("beam_width_mm"),
            beam_depth_mm=geometry_values.get("beam_depth_mm"),
            clear_span_mm=geometry_values.get("clear_span_mm"),
            effective_span_mm=geometry_values.get("effective_span_mm"),
            beam_length_mm=geometry_values.get("beam_length_mm"),
            beam_orientation=geometry_values.get("beam_orientation"),
            station_start=geometry_values.get("station_start"),
            station_end=geometry_values.get("station_end"),
            concrete_grade=materials.get("concrete_grade"),
            steel_grade=materials.get("steel_grade"),
            cover_top_mm=materials.get("cover_top_mm"),
            cover_bottom_mm=materials.get("cover_bottom_mm"),
            cover_side_mm=materials.get("cover_side_mm"),
            development_length_table=rule_refs["development_length_table"],
            hook_rule=rule_refs["hook_rule"],
            lap_rule=rule_refs["lap_rule"],
            bend_rule=rule_refs["bend_rule"],
            anchorage_rule=rule_refs["anchorage_rule"],
            splice_rule=rule_refs["splice_rule"],
            estimator_rules=rule_refs["estimator_rules"],
            calculation_status=calculation_status,
            traceability=self._build_traceability(spec, association, model, materials),
        )

    @staticmethod
    def _project_metadata(
        model: dict[str, Any],
        drawing_models: List[dict[str, Any]],
    ) -> dict[str, str]:
        primary = drawing_models[0] if drawing_models else {}
        workspace = model.get("project_workspace", {})
        return {
            "drawing_id": str(primary.get("drawing_id", "")),
            "project_id": str(workspace.get("project_id", "")),
        }

    @staticmethod
    def _resolve_geometry_values(
        beam_mark: str,
        association: dict[str, Any],
        index: PhaseFRegistryIndex,
    ) -> dict[str, Any]:
        if not beam_mark or not association:
            return {}
        if str(association.get("association_status", "")) != STATUS_VALID:
            return {}

        beam = index.beam_record(beam_mark)
        if not beam:
            return {}

        section = beam.get("beam_section") or beam.get("dimensions", {}).get("section", {})
        length_model = beam.get("length_model", {})
        geometry = beam.get("geometry", {})
        stationing = beam.get("stationing", {})
        centerline = geometry.get("centerline", {})

        return {
            "beam_width_mm": _numeric_from_field(section.get("width")),
            "beam_depth_mm": _numeric_from_field(section.get("depth")),
            "clear_span_mm": _numeric_from_field(length_model.get("clear_span")),
            "effective_span_mm": _numeric_from_field(length_model.get("effective_span")),
            "beam_length_mm": _numeric_from_field(length_model.get("centerline_length"))
            or _numeric_from_field(geometry.get("length_mm")),
            "beam_orientation": centerline.get("orientation") or geometry.get("orientation"),
            "station_start": stationing.get("station_start"),
            "station_end": stationing.get("station_end"),
        }

    @staticmethod
    def _resolve_phase_f_references(
        beam_mark: str,
        association: dict[str, Any],
        index: PhaseFRegistryIndex,
    ) -> dict[str, str]:
        refs = {
            "beam_geometry_id": str(association.get("beam_geometry_id", "")),
            "beam_section_id": str(association.get("beam_section_id", "")),
            "coordinate_system_id": str(association.get("coordinate_system_id", "")),
            "knowledge_graph_node_id": str(association.get("knowledge_graph_node_id", "")),
            "length_model_id": "",
            "support_model_id": "",
        }
        if not beam_mark:
            return refs

        beam = index.beam_record(beam_mark)
        if beam:
            engineering_refs = beam.get("engineering_references", {})
            refs["length_model_id"] = str(
                engineering_refs.get("length_model_id") or length_id(beam_mark)
            )
            refs["support_model_id"] = str(
                engineering_refs.get("support_model_id") or support_beam_id(beam_mark)
            )
            if not refs["beam_geometry_id"]:
                refs["beam_geometry_id"] = str(engineering_refs.get("beam_id") or f"BEAM::{beam_mark}")
            if not refs["coordinate_system_id"]:
                refs["coordinate_system_id"] = str(
                    engineering_refs.get("coordinate_system_id") or f"ECS::{beam_mark}"
                )
        else:
            refs["length_model_id"] = length_id(beam_mark)
            refs["support_model_id"] = support_beam_id(beam_mark)

        return refs

    @staticmethod
    def _resolve_status(
        association: dict[str, Any],
        geometry_values: dict[str, Any],
        materials: dict[str, Any],
    ) -> str:
        if not association:
            return STATUS_INCOMPLETE

        has_geometry = all(
            geometry_values.get(field) is not None
            for field in (
                "beam_width_mm",
                "beam_depth_mm",
                "clear_span_mm",
                "effective_span_mm",
            )
        )
        has_materials = all(
            materials.get(field) is not None
            for field in ("concrete_grade", "steel_grade", "cover_top_mm")
        )

        if (
            str(association.get("association_status", "")) == STATUS_VALID
            and has_geometry
            and has_materials
        ):
            return STATUS_COMPLETE
        if association.get("association_id"):
            return STATUS_PARTIAL
        return STATUS_INCOMPLETE

    @staticmethod
    def _build_traceability(
        spec: dict[str, Any],
        association: dict[str, Any],
        model: dict[str, Any],
        materials: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "lineage": [
                "Engineering Calculation Context",
                "Geometry Association",
                "Engineering Specification",
                "Phase F Geometry",
                "General Notes",
                "Estimator Rules",
                "Project Defaults",
            ],
            "specification_id": spec.get("specification_id"),
            "association_id": association.get("association_id"),
            "association_status": association.get("association_status"),
            "specification_status": spec.get("specification_status"),
            "material_sources": materials.get("sources", {}),
            "association_traceability": association.get("traceability", {}),
            "specification_traceability": spec.get("traceability", {}),
            "rules_reference": "RULE::PROJECT",
            "estimator_reference": "RULE::ESTIMATOR",
            "phase_f_beam_count": len(model.get("beams", [])),
        }


def _numeric_from_field(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        raw = value.get("value")
        if raw is not None:
            return float(raw)
    numeric = engineering_value_numeric(value)
    if numeric is not None:
        return float(numeric)
    return None
