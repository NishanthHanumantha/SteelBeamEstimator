"""Load K.1 intent outputs and supporting engineering artifacts for resolution."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from src.estimator_validation.comparison_utils import load_json_if_exists

PHASE = "Phase K.1.1"
MODEL_VERSION = "6.0.1"
ENGINE_VERSION = "1.0.0"
OUTPUT_DIR_REL = Path("data/output/engineering_intent_resolution")
INTENT_OUTPUT_REL = Path("data/output/engineering_intent")
PRIORITY_CONFIG_REL = Path("config/engineering_intent_priority.yaml")

_ID_PATTERN = re.compile(r"::(\d+)$")


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    root = project_root or Path.cwd()
    phase_e = root / Path("data/output/phase_e")
    phase_f = root / Path("data/output/phase_f")
    phase_g = root / Path("data/output/phase_g")
    phase_h = root / Path("data/output/phase_h")
    phase_i = root / Path("data/output/phase_i")
    intent_dir = root / INTENT_OUTPUT_REL
    return {
        "output_dir": root / OUTPUT_DIR_REL,
        "priority_config": root / PRIORITY_CONFIG_REL,
        "intent_registry": intent_dir / "engineering_intent_registry.json",
        "intent_objects": intent_dir / "engineering_intent_objects.json",
        "intent_traceability": intent_dir / "engineering_intent_traceability.json",
        "intent_statistics": intent_dir / "engineering_intent_statistics.json",
        "engineering_objects": phase_g / "g_5_1_engineering_objects/engineering_objects.json",
        "engineering_specifications": phase_h / "h_1_engineering_specifications/engineering_specifications.json",
        "geometry_associations": phase_h / "h_2_geometry_association/geometry_associations.json",
        "calculation_contexts": phase_i / "i_1_calculation_context/calculation_contexts.json",
        "reinforcement_objects": phase_i / "i_2_reinforcement_engine/reinforcement_objects.json",
        "engineering_rules": phase_e / "general_notes_engineering_rules.json",
        "development_length_table": phase_e / "development_length_table.json",
        "material_specifications": phase_e / "material_specifications.json",
        "project_workspace": phase_f / "f_7_project_workspace/project_workspace.json",
        "beam_geometry_model": phase_f / "beam_geometry_model.json",
        "support_graph": phase_f / "f_3_support_and_section/support_graph.json",
        "beam_supports": phase_f / "f_1_framing_geometry/beam_supports.json",
        "project_engineering_graph": phase_f / "f_6_engineering_context/project_engineering_graph.json",
        "clear_spans": phase_f / "f_4_engineering_length/clear_spans.json",
        "recovery_registry": root / Path("data/output/engineering_recovery/recovery_registry.json"),
        "decision_registry": root / OUTPUT_DIR_REL / "engineering_decision_registry.json",
    }


def max_id_sequence(items: List[str], prefix: str) -> int:
    maximum = 0
    for item in items:
        if not str(item).startswith(prefix):
            continue
        match = _ID_PATTERN.search(str(item))
        if match:
            maximum = max(maximum, int(match.group(1)))
    return maximum


class ResolutionCollector:
    """Collect K.1 intent artifacts and supporting engineering context."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.paths = default_paths(project_root)
        self.load_status: Dict[str, bool] = {}

    def collect(self) -> dict[str, Any]:
        payloads: Dict[str, Any] = {}
        skip_keys = {"output_dir", "priority_config", "decision_registry"}
        for key, path in self.paths.items():
            if key in skip_keys:
                continue
            payloads[key] = load_json_if_exists(path)
            self.load_status[key] = payloads[key] is not None

        intent_registry = payloads.get("intent_registry") or {}
        intent_objects_payload = payloads.get("intent_objects") or {}
        intent_trace_payload = payloads.get("intent_traceability") or {}

        intent_entries = list(intent_registry.get("entries") or [])
        intent_objects = list(intent_objects_payload.get("objects") or [])
        intent_traces = list(intent_trace_payload.get("chains") or [])

        # Prefer full intent objects; fall back to registry reconstruction.
        if not intent_objects and intent_entries:
            intent_objects = [
                {
                    "intent_id": entry.get("intent_id"),
                    "intent_key": entry.get("intent_key"),
                    "intent_type": entry.get("intent_type"),
                    "source_bar_id": entry.get("source_bar_id"),
                    "source_engineering_object_id": entry.get("source_engineering_object_id"),
                    "reconstructed_object_id": entry.get("reconstructed_object_id"),
                    "beam_id": entry.get("beam_id"),
                    "support_zone": _zone_from_key(str(entry.get("intent_key") or "")),
                    "specification_id": entry.get("specification_id"),
                    "context_id": entry.get("context_id"),
                    "engineering_justification": entry.get("engineering_justification"),
                    "evidence": {
                        "engineering_rule": entry.get("engineering_rule"),
                        "general_note_id": entry.get("general_note_id"),
                        "evidence_confidence": entry.get("evidence_confidence", 100.0),
                        "engineering_justification": entry.get("engineering_justification"),
                    },
                }
                for entry in intent_entries
            ]

        for obj in intent_objects:
            if not obj.get("support_zone"):
                obj["support_zone"] = _zone_from_key(str(obj.get("intent_key") or ""))

        existing_contexts = (payloads.get("calculation_contexts") or {}).get("contexts") or []
        contexts_by_beam: Dict[str, dict[str, Any]] = {}
        context_by_id: Dict[str, dict[str, Any]] = {}
        for context in existing_contexts:
            context_id = str(context.get("context_id") or "")
            beam_id = str(context.get("beam_id") or "")
            if context_id:
                context_by_id[context_id] = context
            if beam_id and beam_id not in contexts_by_beam:
                contexts_by_beam[beam_id] = context

        decision_registry_payload = load_json_if_exists(self.paths["decision_registry"])
        existing_decision_keys = {
            str(entry.get("decision_key"))
            for entry in (decision_registry_payload or {}).get("entries") or []
            if entry.get("decision_key")
        }

        decision_ids = [
            str(entry.get("decision_id"))
            for entry in (decision_registry_payload or {}).get("entries") or []
            if entry.get("decision_id")
        ]

        return {
            "paths": self.paths,
            "load_status": dict(self.load_status),
            "intent_entries": intent_entries,
            "intent_objects": intent_objects,
            "intent_traces": intent_traces,
            "intent_statistics": payloads.get("intent_statistics") or {},
            "engineering_objects": (payloads.get("engineering_objects") or {}).get("objects") or [],
            "engineering_specifications": (payloads.get("engineering_specifications") or {}).get("specifications")
            or [],
            "calculation_contexts": existing_contexts,
            "contexts_by_beam": contexts_by_beam,
            "context_by_id": context_by_id,
            "reinforcement_objects": payloads.get("reinforcement_objects") or {},
            "engineering_rules": payloads.get("engineering_rules") or {},
            "development_length_table": payloads.get("development_length_table") or {},
            "material_specifications": payloads.get("material_specifications") or {},
            "beam_supports": payloads.get("beam_supports") or {},
            "support_graph": payloads.get("support_graph") or {},
            "project_engineering_graph": payloads.get("project_engineering_graph") or {},
            "clear_spans": payloads.get("clear_spans") or {},
            "beam_geometry_model": payloads.get("beam_geometry_model") or {},
            "recovery_registry": payloads.get("recovery_registry") or {},
            "existing_decision_keys": existing_decision_keys,
            "existing_decision_entries": list((decision_registry_payload or {}).get("entries") or []),
            "id_counters": {
                "decision": max_id_sequence(decision_ids, "DECISION::"),
            },
        }


def _zone_from_key(intent_key: str) -> str:
    parts = intent_key.split("::")
    if len(parts) >= 3:
        return parts[-1]
    return "UNKNOWN"
