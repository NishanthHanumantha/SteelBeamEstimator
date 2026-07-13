"""Collect and index all Phase L.2 audit inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from audit_loader import AuditLoader, load_config


class AuditCollector:
    """Collect snapshot of all available data for the audit engine. Read-only."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root
        self._loader = AuditLoader(project_root)

    def collect(self) -> Dict[str, Any]:
        raw = self._loader.load()
        config = load_config(self._loader.paths["config"])
        payloads = raw["payloads"]

        # Prefer V6 outputs; fall back to V5 reference
        def _best(v6_key: str, v5_key: str) -> Any:
            v6 = payloads.get(v6_key)
            return v6 if v6 is not None else payloads.get(v5_key)

        return {
            "config": config,
            "load_status": raw["load_status"],
            "paths": raw["paths"],
            "project_root": raw["project_root"],
            "src_root": raw["src_root"],
            "payloads": payloads,
            # Active pipeline data (v6 preferred, v5 fallback)
            "engineering_objects": _best("v6_engineering_objects", "v5_engineering_objects"),
            "reinforcement_objects": _best("v6_reinforcement_objects", "v5_reinforcement_objects"),
            "calculation_contexts": _best("v6_calculation_contexts", "v5_calculation_contexts"),
            "readiness": _best("v6_readiness", "v5_readiness"),
            "cut_length": _best("v6_cut_length", "v5_cut_length"),
            "development_length": _best("v6_development_length", "v5_development_length"),
            "hook_results": _best("v6_hook_results", "v5_hook_results"),
            "lap_results": _best("v6_lap_results", "v5_lap_results"),
            "steel_weight": _best("v6_steel_weight", "v5_steel_weight"),
            "bbs_results": _best("v6_bbs_results", "v5_bbs_results"),
            "beam_schedule": _best("v6_beam_schedule", "v5_beam_schedule"),
            "engineering_reports": _best("v6_engineering_reports", "v5_engineering_reports"),
            "v6_decisions": payloads.get("v6_decisions"),
            "v6_intents": payloads.get("v6_intents"),
            "v5_engineering_gap": payloads.get("v5_engineering_gap"),
            "v5_accuracy_stats": payloads.get("v5_accuracy_stats"),
            "l1_gap_report": payloads.get("l1_gap_report"),
            "l1_role_gap": payloads.get("l1_role_gap"),
            "l1_rule_gap": payloads.get("l1_rule_gap"),
            "data_source": "V6+V5_REFERENCE" if payloads.get("v5_engineering_objects") else "V6_ONLY",
        }
