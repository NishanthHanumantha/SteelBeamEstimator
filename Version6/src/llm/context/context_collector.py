"""Collect engineering information from supplied objects."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from src.estimator_validation.comparison_utils import load_json_if_exists

OBJECT_CATEGORY_ALIASES = {
    "beam": "beams",
    "beams": "beams",
    "beam_schedule": "beam_schedule",
    "reinforcement": "reinforcement",
    "general_notes": "general_notes",
    "geometry": "geometry",
    "supports": "supports",
    "dimensions": "dimensions",
    "material_properties": "material_properties",
    "engineering_graph": "engineering_graph",
    "calculation_context": "calculation_context",
}


class ContextCollector:
    """Collect deterministic engineering sections from supplied objects."""

    def collect(self, engineering_objects: Dict[str, Any]) -> Dict[str, Any]:
        collected: Dict[str, Any] = {}
        for key, value in engineering_objects.items():
            normalized = OBJECT_CATEGORY_ALIASES.get(key, key)
            if value is None:
                continue
            if self._is_empty(value):
                continue
            collected[normalized] = value
        return collected

    @staticmethod
    def load_production_snapshot(project_root: Path | None = None) -> Dict[str, Any]:
        """Load a minimal deterministic snapshot from Version6 production artifacts."""
        root = project_root or Path.cwd()
        output = root / "data" / "output"
        phase_f = output / "phase_f"
        phase_e = output / "phase_e"
        phase_i = output / "phase_i"

        beams = load_json_if_exists(phase_f / "f_1_framing_geometry" / "beam_supports.json")
        reinforcement_payload = load_json_if_exists(
            phase_i / "i_2_reinforcement_engine" / "reinforcement_objects.json"
        )
        general_notes = load_json_if_exists(phase_e / "general_notes_engineering_rules.json")
        calc_context = load_json_if_exists(phase_i / "i_1_calculation_context" / "calculation_contexts.json")
        geometry = load_json_if_exists(phase_f / "f_3_support_and_section" / "support_graph.json")
        engineering_graph = load_json_if_exists(
            phase_f / "f_6_engineering_context" / "project_engineering_graph.json"
        )
        material = load_json_if_exists(phase_e / "material_specifications.json")
        dimensions = load_json_if_exists(phase_f / "f_1_framing_geometry" / "beam_dimensions.json")

        reinforcement = None
        if isinstance(reinforcement_payload, dict):
            reinforcement = {
                "bar_count": reinforcement_payload.get("bar_count"),
                "group_count": reinforcement_payload.get("group_count"),
                "bars": (reinforcement_payload.get("bars") or [])[:5],
            }

        calc_context_summary = None
        if isinstance(calc_context, dict):
            contexts = calc_context.get("contexts") or []
            calc_context_summary = [
                {
                    "context_id": item.get("context_id"),
                    "beam_id": item.get("beam_id"),
                    "concrete_grade": item.get("concrete_grade"),
                    "steel_grade": item.get("steel_grade"),
                    "calculation_status": item.get("calculation_status"),
                }
                for item in contexts[:5]
            ]

        return {
            "beams": beams,
            "reinforcement": reinforcement,
            "general_notes": _summarize_general_notes(general_notes),
            "calculation_context": calc_context_summary,
            "geometry": _summarize_geometry(geometry),
            "supports": beams,
            "dimensions": dimensions,
            "material_properties": material,
            "engineering_graph": _summarize_graph(engineering_graph),
            "beam_schedule": _summarize_beam_schedule(calc_context_summary),
        }

    @staticmethod
    def _is_empty(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, (list, dict, str)) and len(value) == 0:
            return True
        return False


def _summarize_general_notes(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    return {
        "project_information": payload.get("project_information"),
        "material_specifications": payload.get("material_specifications"),
        "development_tables_present": bool(payload.get("development_tables")),
    }


def _summarize_geometry(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    return {
        "phase": payload.get("phase"),
        "beam_node_count": payload.get("beam_node_count"),
        "support_node_count": payload.get("support_node_count"),
        "edge_count": payload.get("edge_count"),
    }


def _summarize_graph(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    return {
        "project_id": payload.get("project_id"),
        "node_count": payload.get("node_count"),
        "edge_count": payload.get("edge_count"),
    }


def _summarize_beam_schedule(contexts: Any) -> Any:
    if not isinstance(contexts, list):
        return contexts
    return [{"beam_id": item.get("beam_id"), "context_id": item.get("context_id")} for item in contexts]


def build_section_payload(
    section_name: str,
    definition_objects: tuple[str, ...],
    collected: Dict[str, Any],
) -> Dict[str, Any] | None:
    payload: Dict[str, Any] = {}
    for obj_key in definition_objects:
        if obj_key in collected and not ContextCollector._is_empty(collected[obj_key]):
            payload[obj_key] = collected[obj_key]
    if not payload:
        return None
    return {section_name: payload}
