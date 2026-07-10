"""Collect Engineering Decisions and production inputs for execution."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from src.estimator_validation.comparison_utils import load_json_if_exists

PHASE = "Phase K.2"
MODEL_VERSION = "6.1.0"
ENGINE_VERSION = "1.0.0"
PHASE_FOLDER = "PhaseK.2 - engineering_decision_execution"
OUTPUT_DIR_REL = Path("data/output") / PHASE_FOLDER
CONFIG_REL = Path("config/engineering_decision_execution.yaml")
DECISION_OUTPUT_REL = Path("data/output/engineering_intent_resolution")
INTENT_OUTPUT_REL = Path("data/output/engineering_intent")
VALIDATION_OUTPUT_REL = Path("data/output/PhaseK.2.1 - engineering_decision_validation")
VALIDATION_CONFIG_REL = Path("config/engineering_decision_validation.yaml")

_ID_PATTERN = re.compile(r"::(\d+)$")


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    root = project_root or Path.cwd()
    phase_e = root / "data/output/phase_e"
    phase_f = root / "data/output/phase_f"
    phase_g = root / "data/output/phase_g"
    phase_h = root / "data/output/phase_h"
    phase_i = root / "data/output/phase_i"
    decision_dir = root / DECISION_OUTPUT_REL
    intent_dir = root / INTENT_OUTPUT_REL
    output_dir = root / OUTPUT_DIR_REL
    return {
        "output_dir": output_dir,
        "config": root / CONFIG_REL,
        "decision_registry": decision_dir / "engineering_decision_registry.json",
        "decision_objects": decision_dir / "engineering_decision_objects.json",
        "decision_traceability": decision_dir / "engineering_intent_resolution_traceability.json",
        "intent_registry": intent_dir / "engineering_intent_registry.json",
        "intent_objects": intent_dir / "engineering_intent_objects.json",
        "engineering_objects": phase_g / "g_5_1_engineering_objects/engineering_objects.json",
        "engineering_specifications": phase_h / "h_1_engineering_specifications/engineering_specifications.json",
        "geometry_associations": phase_h / "h_2_geometry_association/geometry_associations.json",
        "calculation_contexts": phase_i / "i_1_calculation_context/calculation_contexts.json",
        "reinforcement_objects": phase_i / "i_2_reinforcement_engine/reinforcement_objects.json",
        "engineering_calculation_results": phase_i
        / "i_2_2_calculation_result_framework/engineering_calculation_results.json",
        "cut_length_results": phase_i / "i_6_cut_length/cut_length_results.json",
        "steel_weight_results": phase_i / "i_11_steel_weight/steel_weight_results.json",
        "bbs_results": phase_i / "i_10_bbs/bbs_results.json",
        "beam_schedule_results": phase_i / "i_15_beam_schedule/beam_schedule_results.json",
        "engineering_reports": phase_i / "i_16_engineering_report/engineering_reports.json",
        "excel_export_statistics": phase_i / "i_17_excel_export/excel_export_statistics.json",
        "dependency_graph": phase_i / "i_4_6_calculation_dependency/dependency_graph.json",
        "engineering_rules": phase_e / "general_notes_engineering_rules.json",
        "development_length_table": phase_e / "development_length_table.json",
        "beam_geometry_model": phase_f / "beam_geometry_model.json",
        "beam_supports": phase_f / "f_1_framing_geometry/beam_supports.json",
        "project_engineering_graph": phase_f / "f_6_engineering_context/project_engineering_graph.json",
        "recovery_registry": root / "data/output/engineering_recovery/recovery_registry.json",
        "execution_registry": output_dir / "execution_registry.json",
        "validated_decision_registry": root
        / VALIDATION_OUTPUT_REL
        / "validated_decision_registry.json",
        "validated_decision_registry_compat": root
        / VALIDATION_OUTPUT_REL
        / "decision_validation_registry.json",
        "validation_config": root / VALIDATION_CONFIG_REL,
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


class DecisionCollector:
    """Collect K.1.1 decisions and supporting production artifacts."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.paths = default_paths(project_root)
        self.load_status: Dict[str, bool] = {}

    def collect(self) -> dict[str, Any]:
        payloads: Dict[str, Any] = {}
        skip = {
            "output_dir",
            "config",
            "execution_registry",
            "validation_config",
            "validated_decision_registry",
            "validated_decision_registry_compat",
        }
        for key, path in self.paths.items():
            if key in skip:
                continue
            payloads[key] = load_json_if_exists(path)
            self.load_status[key] = payloads[key] is not None

        decision_registry = payloads.get("decision_registry") or {}
        decision_objects_payload = payloads.get("decision_objects") or {}
        all_decisions = list(decision_objects_payload.get("objects") or [])
        if not all_decisions:
            all_decisions = list(decision_registry.get("entries") or [])

        # Phase K.2.1 execution gate — only VALIDATED decisions may execute.
        validation_gate = self._apply_validation_gate(all_decisions)
        decisions = list(validation_gate.get("decisions") or [])

        contexts = (payloads.get("calculation_contexts") or {}).get("contexts") or []
        context_by_id = {
            str(item.get("context_id")): item for item in contexts if item.get("context_id")
        }
        contexts_by_beam: Dict[str, dict[str, Any]] = {}
        for item in contexts:
            beam_id = str(item.get("beam_id") or "")
            if beam_id and beam_id not in contexts_by_beam:
                contexts_by_beam[beam_id] = item

        specs = (payloads.get("engineering_specifications") or {}).get("specifications") or []
        spec_by_id = {
            str(item.get("specification_id")): item for item in specs if item.get("specification_id")
        }

        objects = (payloads.get("engineering_objects") or {}).get("objects") or []
        object_by_id = {
            str(item.get("engineering_object_id") or item.get("object_id")): item
            for item in objects
            if item.get("engineering_object_id") or item.get("object_id")
        }

        intent_objects = (payloads.get("intent_objects") or {}).get("objects") or []
        intent_by_id = {
            str(item.get("intent_id")): item for item in intent_objects if item.get("intent_id")
        }

        existing_execution = load_json_if_exists(self.paths["execution_registry"])
        existing_execution_keys = {
            str(entry.get("execution_key"))
            for entry in (existing_execution or {}).get("entries") or []
            if entry.get("execution_key")
        }
        existing_execution_ids = [
            str(entry.get("execution_id"))
            for entry in (existing_execution or {}).get("entries") or []
            if entry.get("execution_id")
        ]

        return {
            "paths": self.paths,
            "load_status": dict(self.load_status),
            "decisions": decisions,
            "decision_registry_entries": list(decision_registry.get("entries") or []),
            "decision_traces": list((payloads.get("decision_traceability") or {}).get("chains") or []),
            "intent_objects": intent_objects,
            "intent_by_id": intent_by_id,
            "intent_entries": list((payloads.get("intent_registry") or {}).get("entries") or []),
            "engineering_objects": objects,
            "object_by_id": object_by_id,
            "specifications": specs,
            "spec_by_id": spec_by_id,
            "calculation_contexts": contexts,
            "context_by_id": context_by_id,
            "contexts_by_beam": contexts_by_beam,
            "reinforcement_objects": payloads.get("reinforcement_objects") or {},
            "engineering_calculation_results": payloads.get("engineering_calculation_results") or {},
            "cut_length_results": payloads.get("cut_length_results") or {},
            "steel_weight_results": payloads.get("steel_weight_results") or {},
            "bbs_results": payloads.get("bbs_results") or {},
            "beam_schedule_results": payloads.get("beam_schedule_results") or {},
            "engineering_reports": payloads.get("engineering_reports") or {},
            "excel_export_statistics": payloads.get("excel_export_statistics") or {},
            "dependency_graph": payloads.get("dependency_graph") or {},
            "engineering_rules": payloads.get("engineering_rules") or {},
            "development_length_table": payloads.get("development_length_table") or {},
            "beam_geometry_model": payloads.get("beam_geometry_model") or {},
            "beam_supports": payloads.get("beam_supports") or {},
            "project_engineering_graph": payloads.get("project_engineering_graph") or {},
            "recovery_registry": payloads.get("recovery_registry") or {},
            "existing_execution_keys": existing_execution_keys,
            "existing_execution_entries": list((existing_execution or {}).get("entries") or []),
            "validation_gate": validation_gate,
            "all_decisions_count": len(all_decisions),
            "id_counters": {
                "execution": max_id_sequence(existing_execution_ids, "EXEC::"),
            },
        }

    def _apply_validation_gate(self, all_decisions: List[dict[str, Any]]) -> dict[str, Any]:
        """Entry-point gate: consume only validated decisions when K.2.1 is enabled."""
        validation_config_path = self.paths.get("validation_config")
        validation_enabled = True
        if validation_config_path and validation_config_path.exists():
            try:
                import yaml  # type: ignore

                payload = yaml.safe_load(validation_config_path.read_text(encoding="utf-8")) or {}
                if isinstance(payload, dict) and "enable" in payload:
                    validation_enabled = bool(payload.get("enable"))
            except Exception:
                # Fallback simple parse
                text = validation_config_path.read_text(encoding="utf-8")
                for raw in text.splitlines():
                    line = raw.split("#", 1)[0].strip()
                    if line.startswith("enable:"):
                        validation_enabled = line.split(":", 1)[1].strip().lower() == "true"

        if not validation_enabled:
            # MODEL_VERSION 6.1.0 behaviour — all K.1.1 decisions flow through.
            return {
                "enabled": False,
                "mode": "PASSTHROUGH_6_1_0",
                "source_decision_count": len(all_decisions),
                "allowed_decision_count": len(all_decisions),
                "blocked_decision_count": 0,
                "decisions": all_decisions,
                "allowed_ids": [
                    str(item.get("decision_id"))
                    for item in all_decisions
                    if item.get("decision_id")
                ],
            }

        registry_payload = load_json_if_exists(self.paths["validated_decision_registry"])
        if not registry_payload:
            registry_payload = load_json_if_exists(self.paths["validated_decision_registry_compat"])
        if not registry_payload:
            return {
                "enabled": True,
                "mode": "BLOCKED_NO_REGISTRY",
                "source_decision_count": len(all_decisions),
                "allowed_decision_count": 0,
                "blocked_decision_count": len(all_decisions),
                "decisions": [],
                "allowed_ids": [],
                "reason": "Validated decision registry missing — run Phase K.2.1 first.",
            }

        allowed_ids = {
            str(item)
            for item in (registry_payload.get("execution_allowed_ids") or [])
            if item
        }
        # Also accept entries marked execution_allowed for robustness.
        for entry in registry_payload.get("entries") or []:
            if entry.get("execution_allowed") and entry.get("decision_id"):
                allowed_ids.add(str(entry.get("decision_id")))

        filtered = [
            decision
            for decision in all_decisions
            if str(decision.get("decision_id") or "") in allowed_ids
        ]
        return {
            "enabled": True,
            "mode": "VALIDATED_ONLY",
            "source_decision_count": len(all_decisions),
            "allowed_decision_count": len(filtered),
            "blocked_decision_count": len(all_decisions) - len(filtered),
            "decisions": filtered,
            "allowed_ids": sorted(allowed_ids),
        }
