"""Load production, discovery, QA, and J.1 recovery artifacts for expansion."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Set

from src.engineering_recovery.recovery_collector import max_id_sequence
from src.estimator_validation.comparison_utils import load_json_if_exists

PHASE = "Phase J.2"
MODEL_VERSION = "5.28.0"
ENGINE_VERSION = "1.0.0"
EXPANSION_VERSION = "5.28.0"
SIMILARITY_THRESHOLD = 85.0
OUTPUT_DIR_REL = Path("data/output/engineering_recovery_expansion")


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    root = project_root or Path.cwd()
    phase_g = root / Path("data/output/phase_g")
    phase_h = root / Path("data/output/phase_h")
    phase_i = root / Path("data/output/phase_i")
    return {
        "output_dir": root / OUTPUT_DIR_REL,
        "object_audit_dir": root / Path("data/output/engineering_object_audit"),
        "duplicate_audit_dir": root / Path("data/output/duplicate_legitimacy_audit"),
        "discovery_dir": root / Path("data/output/reinforcement_discovery_analysis"),
        "j1_recovery_dir": root / Path("data/output/engineering_recovery"),
        "engineering_objects": phase_g / "g_5_1_engineering_objects/engineering_objects.json",
        "engineering_specifications": phase_h / "h_1_engineering_specifications/engineering_specifications.json",
        "calculation_contexts": phase_i / "i_1_calculation_context/calculation_contexts.json",
        "reinforcement_objects": phase_i / "i_2_reinforcement_engine/reinforcement_objects.json",
        "project_workspace": root / Path("data/output/phase_f/project_workspace.json"),
        "beam_geometry_model": root / Path("data/output/phase_f/beam_geometry_model.json"),
    }


class CandidateLoader:
    """Collect inputs required for recovery expansion analysis."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.paths = default_paths(project_root)
        self.load_status: Dict[str, bool] = {}

    def collect(self) -> dict[str, Any]:
        payloads: Dict[str, Any] = {}
        skip_keys = {
            "output_dir",
            "object_audit_dir",
            "duplicate_audit_dir",
            "discovery_dir",
            "j1_recovery_dir",
        }
        for key, path in self.paths.items():
            if key in skip_keys:
                continue
            payloads[key] = load_json_if_exists(path)
            self.load_status[key] = payloads[key] is not None

        inventory_payload = load_json_if_exists(
            self.paths["discovery_dir"] / "reinforcement_inventory.json"
        )
        payloads["reinforcement_inventory"] = inventory_payload
        self.load_status["reinforcement_inventory"] = inventory_payload is not None

        audit_files = {
            "object_decision_matrix": (self.paths["object_audit_dir"], "engineering_object_decision_matrix.json"),
            "object_creation_audit": (self.paths["object_audit_dir"], "engineering_object_creation_audit.json"),
            "duplicate_group_analysis": (self.paths["duplicate_audit_dir"], "duplicate_group_analysis.json"),
            "engineering_recommendations": (
                self.paths["object_audit_dir"],
                "engineering_recommendations.json",
            ),
            "discovery_gap_analysis": (
                self.paths["discovery_dir"],
                "reinforcement_discovery_gap_analysis.json",
            ),
        }
        for key, (directory, filename) in audit_files.items():
            payloads[key] = load_json_if_exists(directory / filename)
            self.load_status[key] = payloads[key] is not None

        j1_registry = load_json_if_exists(self.paths["j1_recovery_dir"] / "recovery_registry.json") or {}
        expansion_registry = load_json_if_exists(self.paths["output_dir"] / "expansion_registry.json") or {}
        payloads["j1_recovery_registry"] = j1_registry
        payloads["expansion_registry"] = expansion_registry
        self.load_status["j1_recovery_registry"] = bool(j1_registry)
        self.load_status["expansion_registry"] = bool(expansion_registry)

        inventory = (inventory_payload or {}).get("inventory") or []
        inventory_by_id = {str(item.get("discovery_id")): item for item in inventory}

        decision_records = (payloads.get("object_decision_matrix") or {}).get("records") or []
        decision_by_id = {str(item.get("discovery_id")): item for item in decision_records}

        audit_records = (payloads.get("object_creation_audit") or {}).get("audits") or []
        audit_by_id = {str(item.get("discovery_id")): item for item in audit_records}

        existing_objects = (payloads.get("engineering_objects") or {}).get("objects") or []
        existing_specs = (payloads.get("engineering_specifications") or {}).get("specifications") or []
        existing_contexts = (payloads.get("calculation_contexts") or {}).get("contexts") or []
        existing_bars = (payloads.get("reinforcement_objects") or {}).get("bars") or []
        existing_groups = (payloads.get("reinforcement_objects") or {}).get("groups") or []

        j1_recovered_ids = {
            str(entry.get("discovery_id"))
            for entry in (j1_registry.get("entries") or [])
            if entry.get("discovery_id")
        }
        expansion_recovered_ids = {
            str(entry.get("discovery_id"))
            for entry in (expansion_registry.get("entries") or [])
            if entry.get("discovery_id")
        }
        production_discovery_ids = {
            str((bar.get("traceability") or {}).get("discovery_id"))
            for bar in existing_bars
            if (bar.get("traceability") or {}).get("discovery_id")
        }
        native_production_discovery_ids = {
            discovery_id
            for discovery_id in production_discovery_ids
            if discovery_id not in j1_recovered_ids and discovery_id not in expansion_recovered_ids
        }

        contexts_by_beam: Dict[str, dict[str, Any]] = {}
        context_by_id = {
            str(context.get("context_id")): context for context in existing_contexts if context.get("context_id")
        }
        for context in existing_contexts:
            beam_id = str(context.get("beam_id") or "")
            if beam_id and beam_id not in contexts_by_beam:
                contexts_by_beam[beam_id] = context
        for bar in existing_bars:
            beam_id = str(bar.get("beam_id") or "")
            context = context_by_id.get(str(bar.get("context_id") or ""))
            if beam_id and context and beam_id not in contexts_by_beam:
                contexts_by_beam[beam_id] = context

        id_counters = {
            "recovery": max(
                max_id_sequence(
                    [str(entry.get("recovery_id") or "") for entry in (j1_registry.get("entries") or [])],
                    "RECOVERY",
                ),
                max_id_sequence(
                    [str(entry.get("recovery_id") or "") for entry in (expansion_registry.get("entries") or [])],
                    "RECOVERY",
                ),
            ),
            "expansion": max_id_sequence(
                [str(entry.get("expansion_id") or "") for entry in (expansion_registry.get("entries") or [])],
                "EXPANSION",
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
            "inventory": inventory,
            "inventory_by_id": inventory_by_id,
            "decision_by_id": decision_by_id,
            "audit_by_id": audit_by_id,
            "existing_objects": existing_objects,
            "existing_specs": existing_specs,
            "existing_contexts": existing_contexts,
            "existing_bars": existing_bars,
            "existing_groups": existing_groups,
            "contexts_by_beam": contexts_by_beam,
            "project_workspace": payloads.get("project_workspace") or {},
            "payloads": payloads,
            "id_counters": id_counters,
            "j1_recovered_ids": j1_recovered_ids,
            "expansion_recovered_ids": expansion_recovered_ids,
            "production_discovery_ids": production_discovery_ids,
            "native_production_discovery_ids": native_production_discovery_ids,
            "already_recovered_ids": j1_recovered_ids | expansion_recovered_ids,
            "j1_registry_entries": j1_registry.get("entries") or [],
            "expansion_registry_entries": expansion_registry.get("entries") or [],
        }
