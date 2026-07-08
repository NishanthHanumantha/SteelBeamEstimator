"""Load QA and production artifacts for engineering object recovery."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.estimator_validation.comparison_utils import load_json_if_exists

PHASE = "Phase J.1"
MODEL_VERSION = "5.26.0"
ENGINE_VERSION = "1.0.0"
RECOVERY_VERSION = "5.26.0"
CONFIDENCE_THRESHOLD = 70.0
OUTPUT_DIR_REL = Path("data/output/engineering_recovery")

_ID_PATTERN = re.compile(r"::(\d+)$")


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    root = project_root or Path.cwd()
    phase_g = root / Path("data/output/phase_g")
    phase_h = root / Path("data/output/phase_h")
    phase_i = root / Path("data/output/phase_i")
    phase_e = root / Path("data/output/phase_e")
    return {
        "output_dir": root / OUTPUT_DIR_REL,
        "object_audit_dir": root / Path("data/output/engineering_object_audit"),
        "duplicate_audit_dir": root / Path("data/output/duplicate_legitimacy_audit"),
        "discovery_dir": root / Path("data/output/reinforcement_discovery_analysis"),
        "engineering_objects": phase_g / "g_5_1_engineering_objects/engineering_objects.json",
        "engineering_properties": phase_g / "g_5_3_1_property_parser/engineering_properties.json",
        "resolved_properties": phase_g / "g_5_3_2_property_resolver/resolved_engineering_properties.json",
        "geometry_associations": phase_h / "h_2_geometry_association/geometry_associations.json",
        "engineering_specifications": phase_h / "h_1_engineering_specifications/engineering_specifications.json",
        "calculation_contexts": phase_i / "i_1_calculation_context/calculation_contexts.json",
        "reinforcement_objects": phase_i / "i_2_reinforcement_engine/reinforcement_objects.json",
        "engineering_calculation_results": phase_i
        / "i_2_2_calculation_result_framework/engineering_calculation_results.json",
        "calculation_result_registry": phase_i
        / "i_2_2_calculation_result_framework/calculation_result_registry.json",
        "bbs_results": phase_i / "i_10_bbs/bbs_results.json",
        "engineering_reports": phase_i / "i_16_engineering_reports/engineering_report_results.json",
        "project_workspace": root / Path("data/output/phase_f/project_workspace.json"),
        "engineering_rules": phase_e / "general_notes_engineering_rules.json",
        "beam_geometry_model": root / Path("data/output/phase_f/beam_geometry_model.json"),
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


class RecoveryCollector:
    """Collect recovery inputs from QA outputs and production artifacts."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.paths = default_paths(project_root)
        self.load_status: Dict[str, bool] = {}

    def collect(self) -> dict[str, Any]:
        payloads: Dict[str, Any] = {}
        skip_keys = {"output_dir", "object_audit_dir", "duplicate_audit_dir", "discovery_dir"}
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
            "object_creation_audit": (self.paths["object_audit_dir"], "engineering_object_creation_audit.json"),
            "object_decision_matrix": (self.paths["object_audit_dir"], "engineering_object_decision_matrix.json"),
            "duplicate_group_analysis": (self.paths["duplicate_audit_dir"], "duplicate_group_analysis.json"),
            "duplicate_root_cause_chain": (self.paths["duplicate_audit_dir"], "duplicate_root_cause_chain.json"),
            "duplicate_confidence_scores": (self.paths["duplicate_audit_dir"], "duplicate_confidence_scores.json"),
            "duplicate_decision_matrix": (self.paths["duplicate_audit_dir"], "duplicate_decision_matrix.json"),
        }
        for key, (directory, filename) in audit_files.items():
            payloads[key] = load_json_if_exists(directory / filename)
            self.load_status[key] = payloads[key] is not None

        inventory = (inventory_payload or {}).get("inventory") or []
        inventory_by_id = {str(item.get("discovery_id")): item for item in inventory}

        decision_records = (payloads.get("object_decision_matrix") or {}).get("records") or []
        decision_by_id = {str(item.get("discovery_id")): item for item in decision_records}

        audit_records = (payloads.get("object_creation_audit") or {}).get("audits") or []
        audit_by_id = {str(item.get("discovery_id")): item for item in audit_records}

        legitimacy_by_discovery = self._build_legitimacy_index(payloads)

        existing_objects = (payloads.get("engineering_objects") or {}).get("objects") or []
        existing_specs = (payloads.get("engineering_specifications") or {}).get("specifications") or []
        existing_contexts = (payloads.get("calculation_contexts") or {}).get("contexts") or []
        existing_bars = (payloads.get("reinforcement_objects") or {}).get("bars") or []

        id_counters = {
            "recovery": 0,
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
                [str(item.get("group_id")) for item in (payloads.get("reinforcement_objects") or {}).get("groups") or []],
                "REBAR_GROUP",
            ),
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

        return {
            "paths": {key: str(path) for key, path in self.paths.items()},
            "load_status": dict(self.load_status),
            "inventory": inventory,
            "inventory_by_id": inventory_by_id,
            "decision_by_id": decision_by_id,
            "audit_by_id": audit_by_id,
            "legitimacy_by_discovery": legitimacy_by_discovery,
            "existing_objects": existing_objects,
            "existing_specs": existing_specs,
            "existing_contexts": existing_contexts,
            "existing_bars": existing_bars,
            "existing_groups": (payloads.get("reinforcement_objects") or {}).get("groups") or [],
            "existing_calculation_results": (payloads.get("engineering_calculation_results") or {}).get("results")
            or (payloads.get("engineering_calculation_results") or {}).get("engineering_calculation_results")
            or [],
            "calculation_result_registry": payloads.get("calculation_result_registry") or {},
            "geometry_associations": (payloads.get("geometry_associations") or {}).get("associations") or [],
            "payloads": payloads,
            "id_counters": id_counters,
            "contexts_by_beam": contexts_by_beam,
            "project_workspace": payloads.get("project_workspace") or {},
            "engineering_rules_path": str(self.paths["engineering_rules"]),
        }

    @staticmethod
    def _build_legitimacy_index(payloads: dict[str, Any]) -> Dict[str, dict[str, Any]]:
        index: Dict[str, dict[str, Any]] = {}
        groups = (payloads.get("duplicate_group_analysis") or {}).get("groups") or []
        for group in groups:
            group_meta = {
                "group_id": group.get("group_id"),
                "signature": group.get("signature"),
                "beam_id": group.get("beam_id"),
                "legitimacy_class": group.get("legitimacy_class"),
                "should_suppression_occur": group.get("should_suppression_occur"),
                "confidence_score": group.get("confidence_score"),
                "confidence_band": group.get("confidence_band"),
            }
            for discovery_id in group.get("suppressed_callouts") or []:
                index[str(discovery_id)] = {
                    **group_meta,
                    "suppressed": True,
                }
            for discovery_id in group.get("original_callouts") or []:
                if str(discovery_id) not in index:
                    index[str(discovery_id)] = {
                        **group_meta,
                        "suppressed": False,
                    }
        return index
