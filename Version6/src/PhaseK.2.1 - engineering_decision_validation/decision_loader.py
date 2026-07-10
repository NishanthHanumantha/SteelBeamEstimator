"""Load Engineering Decisions and supporting registries for validation (read-only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set

from src.estimator_validation.comparison_utils import load_json_if_exists

PHASE = "Phase K.2.1"
MODEL_VERSION = "6.2.0"
ENGINE_VERSION = "1.0.0"
PHASE_FOLDER = "PhaseK.2.1 - engineering_decision_validation"
OUTPUT_DIR_REL = Path("data/output") / PHASE_FOLDER
CONFIG_REL = Path("config/engineering_decision_validation.yaml")
DECISION_OUTPUT_REL = Path("data/output/engineering_intent_resolution")
INTENT_OUTPUT_REL = Path("data/output/engineering_intent")
K2_OUTPUT_REL = Path("data/output/PhaseK.2 - engineering_decision_execution")

DEFAULT_CONFIG: Dict[str, Any] = {
    "model_version": MODEL_VERSION,
    "phase": PHASE,
    "enable": True,
    "strict_validation": True,
    "allow_warnings": True,
    "minimum_score": 100,
    "stop_on_invalid": True,
    "export_validation_registry": True,
    "export_statistics": True,
    "fail_on_broken_traceability": True,
    "fail_on_duplicate_execution": True,
    "export_excel_report": True,
}


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    root = project_root or Path.cwd()
    phase_e = root / "data/output/phase_e"
    phase_f = root / "data/output/phase_f"
    phase_g = root / "data/output/phase_g"
    phase_h = root / "data/output/phase_h"
    phase_i = root / "data/output/phase_i"
    decision_dir = root / DECISION_OUTPUT_REL
    intent_dir = root / INTENT_OUTPUT_REL
    k2_dir = root / K2_OUTPUT_REL
    output_dir = root / OUTPUT_DIR_REL
    return {
        "output_dir": output_dir,
        "config": root / CONFIG_REL,
        "decision_registry": decision_dir / "engineering_decision_registry.json",
        "decision_objects": decision_dir / "engineering_decision_objects.json",
        "decision_traceability": decision_dir / "engineering_intent_resolution_traceability.json",
        "decision_graph": decision_dir / "engineering_intent_graph.json",
        "decision_conflicts": decision_dir / "engineering_intent_conflicts.json",
        "decision_merges": decision_dir / "engineering_intent_merges.json",
        "resolution_rules": decision_dir / "engineering_resolution_rules.json",
        "intent_registry": intent_dir / "engineering_intent_registry.json",
        "intent_objects": intent_dir / "engineering_intent_objects.json",
        "engineering_objects": phase_g / "g_5_1_engineering_objects/engineering_objects.json",
        "recovery_registry": root / "data/output/engineering_recovery/recovery_registry.json",
        "calculation_contexts": phase_i / "i_1_calculation_context/calculation_contexts.json",
        "execution_registry": k2_dir / "execution_registry.json",
        "execution_config": root / "config/engineering_decision_execution.yaml",
        "engineering_specifications": phase_h / "h_1_engineering_specifications/engineering_specifications.json",
        "project_engineering_graph": phase_f / "f_6_engineering_context/project_engineering_graph.json",
        "beam_geometry_model": phase_f / "beam_geometry_model.json",
        "beam_supports": phase_f / "f_1_framing_geometry/beam_supports.json",
        "engineering_rules": phase_e / "general_notes_engineering_rules.json",
        "development_length_table": phase_e / "development_length_table.json",
        "steel_weight_results": phase_i / "i_11_steel_weight/steel_weight_results.json",
        "bbs_results": phase_i / "i_10_bbs/bbs_results.json",
        "excel_export_statistics": phase_i / "i_17_excel_export/excel_export_statistics.json",
        "validated_decision_registry": output_dir / "validated_decision_registry.json",
        "decision_validation_registry": output_dir / "decision_validation_registry.json",
    }


def load_validation_config(config_path: Path) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    if not config_path.exists():
        return config
    try:
        import yaml  # type: ignore

        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if isinstance(payload, dict):
            config.update(payload)
        return config
    except ImportError:
        return _load_simple_yaml(config_path, config)


def _load_simple_yaml(path: Path, base: dict[str, Any]) -> dict[str, Any]:
    config = dict(base)
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value.lower() in {"true", "false"}:
            config[key] = value.lower() == "true"
        elif value.isdigit():
            config[key] = int(value)
        else:
            config[key] = value
    return config


class DecisionLoader:
    """Read-only loader for K.2.1 validation inputs. Never executes parsers or engines."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.paths = default_paths(project_root)
        self.load_status: Dict[str, bool] = {}

    def load(self) -> dict[str, Any]:
        payloads: Dict[str, Any] = {}
        skip = {
            "output_dir",
            "config",
            "validated_decision_registry",
            "decision_validation_registry",
            "execution_config",
        }
        for key, path in self.paths.items():
            if key in skip:
                continue
            payloads[key] = load_json_if_exists(path)
            self.load_status[key] = payloads[key] is not None

        self.load_status["execution_config"] = self.paths["execution_config"].exists()
        self.load_status["config"] = self.paths["config"].exists()

        registry = payloads.get("decision_registry") or {}
        objects_payload = payloads.get("decision_objects") or {}
        decisions = list(objects_payload.get("objects") or [])
        if not decisions:
            decisions = list(registry.get("entries") or [])

        indexes = self._build_indexes(payloads, decisions)
        existing = load_json_if_exists(self.paths["validated_decision_registry"])
        if not existing:
            existing = load_json_if_exists(self.paths["decision_validation_registry"])
        existing_keys = {
            str(entry.get("decision_key"))
            for entry in (existing or {}).get("entries") or []
            if entry.get("decision_key")
        }

        return {
            "paths": self.paths,
            "load_status": dict(self.load_status),
            "decisions": decisions,
            "registry_entries": list(registry.get("entries") or []),
            "payloads": payloads,
            "indexes": indexes,
            "artifact_presence": {
                "execution_registry": bool(payloads.get("execution_registry")),
                "execution_config": self.paths["execution_config"].exists(),
                "calculation_contexts": bool(payloads.get("calculation_contexts")),
                "steel_weight_results": bool(payloads.get("steel_weight_results")),
                "bbs_results": bool(payloads.get("bbs_results")),
                "excel_export_statistics": bool(payloads.get("excel_export_statistics")),
                "engineering_rules": bool(payloads.get("engineering_rules")),
                "development_length_table": bool(payloads.get("development_length_table")),
            },
            "existing_validation_keys": existing_keys,
            "existing_validation_entries": list((existing or {}).get("entries") or []),
        }

    def _build_indexes(self, payloads: dict[str, Any], decisions: List[dict[str, Any]]) -> dict[str, Any]:
        eng_objects = list((payloads.get("engineering_objects") or {}).get("objects") or [])
        intents = list((payloads.get("intent_objects") or {}).get("objects") or [])
        contexts = list((payloads.get("calculation_contexts") or {}).get("contexts") or [])
        specs = list((payloads.get("engineering_specifications") or {}).get("specifications") or [])
        graphs = list((payloads.get("decision_graph") or {}).get("graphs") or [])
        conflicts = list((payloads.get("decision_conflicts") or {}).get("conflicts") or [])
        merges = list((payloads.get("decision_merges") or {}).get("merges") or [])
        traces = list((payloads.get("decision_traceability") or {}).get("chains") or [])
        recovery = payloads.get("recovery_registry") or {}
        recovery_entries = list(recovery.get("entries") or recovery.get("objects") or [])

        beam_ids: Set[str] = set()
        beam_model = payloads.get("beam_geometry_model") or {}
        beam_entries = []
        if isinstance(beam_model, dict):
            beam_entries = list(beam_model.get("beams") or beam_model.get("entries") or [])
        elif isinstance(beam_model, list):
            beam_entries = beam_model
        for beam in beam_entries:
            if not isinstance(beam, dict):
                continue
            for key in ("beam_id", "beam_mark", "id"):
                if beam.get(key):
                    beam_ids.add(str(beam.get(key)))
        supports_payload = payloads.get("beam_supports")
        support_entries = []
        if isinstance(supports_payload, dict):
            support_entries = list(
                supports_payload.get("supports")
                or supports_payload.get("entries")
                or supports_payload.get("beams")
                or []
            )
        elif isinstance(supports_payload, list):
            support_entries = supports_payload
        for support in support_entries:
            if isinstance(support, dict) and support.get("beam_id"):
                beam_ids.add(str(support.get("beam_id")))
        for decision in decisions:
            if decision.get("beam_id"):
                beam_ids.add(str(decision.get("beam_id")))

        known_rules: Set[str] = {
            "K.1.1.RESOLVE.PRIORITY",
            "K.1.1.RESOLVE.MERGE",
            "K.1.1.RESOLVE.CONSERVATIVE_FALLBACK",
            "K.1.1.MERGE.SUPPORT_REINFORCEMENT",
            "K.1.1.MERGE.CONTINUOUS_SUPPORT",
        }
        rules = payloads.get("resolution_rules") or {}
        for group in rules.get("merge_groups") or []:
            if group.get("resolution_rule"):
                known_rules.add(str(group.get("resolution_rule")))

        return {
            "decision_ids": {str(item.get("decision_id")) for item in decisions if item.get("decision_id")},
            "decision_keys": {str(item.get("decision_key")) for item in decisions if item.get("decision_key")},
            "engineering_object_ids": {
                str(item.get("engineering_object_id") or item.get("object_id"))
                for item in eng_objects
                if item.get("engineering_object_id") or item.get("object_id")
            },
            "intent_ids": {str(item.get("intent_id")) for item in intents if item.get("intent_id")},
            "context_ids": {str(item.get("context_id")) for item in contexts if item.get("context_id")},
            "specification_ids": {
                str(item.get("specification_id")) for item in specs if item.get("specification_id")
            },
            "beam_ids": beam_ids,
            "graph_ids": {str(item.get("graph_id")) for item in graphs if item.get("graph_id")},
            "conflict_ids": {str(item.get("conflict_id")) for item in conflicts if item.get("conflict_id")},
            "merge_ids": {str(item.get("merge_id")) for item in merges if item.get("merge_id")},
            "recovery_ids": {
                str(item.get("recovery_id") or item.get("object_id") or item.get("engineering_object_id"))
                for item in recovery_entries
                if item.get("recovery_id") or item.get("object_id") or item.get("engineering_object_id")
            },
            "known_rules": known_rules,
            "trace_by_decision": {
                str(item.get("decision_id")): item for item in traces if item.get("decision_id")
            },
            "intent_by_id": {str(item.get("intent_id")): item for item in intents if item.get("intent_id")},
        }
