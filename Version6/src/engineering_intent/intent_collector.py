"""Load production artifacts for engineering intent reconstruction."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from src.estimator_validation.comparison_utils import load_json_if_exists

PHASE = "Phase K.1"
MODEL_VERSION = "6.0.0"
ENGINE_VERSION = "1.0.0"
OUTPUT_DIR_REL = Path("data/output/engineering_intent")

_ID_PATTERN = re.compile(r"::(\d+)$")


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    root = project_root or Path.cwd()
    phase_e = root / Path("data/output/phase_e")
    phase_f = root / Path("data/output/phase_f")
    phase_g = root / Path("data/output/phase_g")
    phase_h = root / Path("data/output/phase_h")
    phase_i = root / Path("data/output/phase_i")
    return {
        "output_dir": root / OUTPUT_DIR_REL,
        "engineering_objects": phase_g / "g_5_1_engineering_objects/engineering_objects.json",
        "engineering_specifications": phase_h / "h_1_engineering_specifications/engineering_specifications.json",
        "geometry_associations": phase_h / "h_2_geometry_association/geometry_associations.json",
        "calculation_contexts": phase_i / "i_1_calculation_context/calculation_contexts.json",
        "reinforcement_objects": phase_i / "i_2_reinforcement_engine/reinforcement_objects.json",
        "engineering_calculation_results": phase_i
        / "i_2_2_calculation_result_framework/engineering_calculation_results.json",
        "engineering_rules": phase_e / "general_notes_engineering_rules.json",
        "development_length_table": phase_e / "development_length_table.json",
        "cover_table": phase_e / "cover_table.json",
        "material_specifications": phase_e / "material_specifications.json",
        "project_workspace": phase_f / "f_7_project_workspace/project_workspace.json",
        "beam_geometry_model": phase_f / "beam_geometry_model.json",
        "support_graph": phase_f / "f_3_support_and_section/support_graph.json",
        "beam_supports": phase_f / "f_1_framing_geometry/beam_supports.json",
        "project_engineering_graph": phase_f / "f_6_engineering_context/project_engineering_graph.json",
        "clear_spans": phase_f / "f_4_engineering_length/clear_spans.json",
        "recovery_registry": root / Path("data/output/engineering_recovery/recovery_registry.json"),
        "expansion_registry": root / Path("data/output/engineering_recovery_expansion/expansion_registry.json"),
        "recovery_validation": root / Path("data/output/engineering_recovery_validation/recovery_validation.json"),
        "production_snapshot": root / Path("data/output/recovery_statistics_validation/production_snapshot.json"),
        "intent_registry": root / OUTPUT_DIR_REL / "engineering_intent_registry.json",
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


class IntentCollector:
    """Collect intent reconstruction inputs from Version6 production artifacts."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.paths = default_paths(project_root)
        self.load_status: Dict[str, bool] = {}

    def collect(self) -> dict[str, Any]:
        payloads: Dict[str, Any] = {}
        skip_keys = {"output_dir", "intent_registry"}
        for key, path in self.paths.items():
            if key in skip_keys:
                continue
            payloads[key] = load_json_if_exists(path)
            self.load_status[key] = payloads[key] is not None

        existing_objects = (payloads.get("engineering_objects") or {}).get("objects") or []
        existing_specs = (payloads.get("engineering_specifications") or {}).get("specifications") or []
        existing_contexts = (payloads.get("calculation_contexts") or {}).get("contexts") or []
        existing_bars = (payloads.get("reinforcement_objects") or {}).get("bars") or []
        existing_groups = (payloads.get("reinforcement_objects") or {}).get("groups") or []

        intent_registry_payload = load_json_if_exists(self.paths["intent_registry"])
        existing_intent_ids = {
            str(entry.get("intent_key"))
            for entry in (intent_registry_payload or {}).get("entries") or []
            if entry.get("intent_key")
        }

        context_by_id = {
            str(context.get("context_id")): context
            for context in existing_contexts
            if context.get("context_id")
        }
        spec_by_id = {
            str(spec.get("specification_id")): spec
            for spec in existing_specs
            if spec.get("specification_id")
        }
        contexts_by_beam: Dict[str, dict[str, Any]] = {}
        for context in existing_contexts:
            beam_id = str(context.get("beam_id") or "")
            if beam_id and beam_id not in contexts_by_beam:
                contexts_by_beam[beam_id] = context

        native_bars = [
            bar
            for bar in existing_bars
            if not (bar.get("traceability") or {}).get("intent_source")
        ]
        intent_bars = [
            bar
            for bar in existing_bars
            if (bar.get("traceability") or {}).get("intent_source")
        ]

        id_counters = {
            "intent": max_id_sequence(
                [str(entry.get("intent_id")) for entry in (intent_registry_payload or {}).get("entries") or []],
                "INTENT",
            ),
            "engineering_object": max_id_sequence(
                [str(item.get("engineering_object_id") or item.get("object_id")) for item in existing_objects],
                "ENG_OBJ",
            ),
            "specification": max_id_sequence(
                [str(item.get("specification_id")) for item in existing_specs],
                "SPEC",
            ),
            "calculation_context": max_id_sequence(
                [str(item.get("context_id")) for item in existing_contexts],
                "CALC_CTX",
            ),
            "rebar": max_id_sequence([str(item.get("bar_id")) for item in existing_bars], "REBAR"),
            "rebar_group": max_id_sequence(
                [str(item.get("group_id")) for item in existing_groups],
                "REBAR_GROUP",
            ),
        }

        return {
            "paths": {key: str(path) for key, path in self.paths.items()},
            "load_status": dict(self.load_status),
            "existing_objects": existing_objects,
            "existing_specs": existing_specs,
            "existing_contexts": existing_contexts,
            "existing_bars": existing_bars,
            "existing_groups": existing_groups,
            "native_bars": native_bars,
            "intent_bars": intent_bars,
            "native_bar_count": len(native_bars),
            "context_by_id": context_by_id,
            "spec_by_id": spec_by_id,
            "contexts_by_beam": contexts_by_beam,
            "existing_intent_ids": existing_intent_ids,
            "intent_registry_entries": (intent_registry_payload or {}).get("entries") or [],
            "id_counters": id_counters,
            "payloads": payloads,
            "project_workspace": payloads.get("project_workspace") or {},
            "engineering_rules": payloads.get("engineering_rules") or {},
            "development_length_table": payloads.get("development_length_table") or {},
            "support_graph": payloads.get("support_graph") or {},
            "beam_supports": payloads.get("beam_supports") or {},
            "project_engineering_graph": payloads.get("project_engineering_graph") or {},
            "geometry_associations": (payloads.get("geometry_associations") or {}).get("associations") or [],
            "recovery_registry": payloads.get("recovery_registry") or {},
            "expansion_registry": payloads.get("expansion_registry") or {},
            "production_snapshot": payloads.get("production_snapshot") or {},
        }
