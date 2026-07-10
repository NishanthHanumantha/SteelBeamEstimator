"""Orchestrate the Engineering Decision Execution pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from calculation_adapter import CalculationAdapter
from decision_execution_context import DecisionExecutionContextBuilder
from decision_mapper import DecisionMapper
from execution_registry import ExecutionRegistryBuilder
from execution_selector import ExecutionSelector
from production_bridge import ProductionBridge


class ExecutionPipeline:
    """Decision → Context → Registry → Adapter → Production Bridge."""

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root
        self._context_builder = DecisionExecutionContextBuilder()
        self._selector = ExecutionSelector()
        self._mapper = DecisionMapper()
        self._registry_builder = ExecutionRegistryBuilder()
        self._adapter = CalculationAdapter(project_root)
        self._bridge = ProductionBridge(project_root)

    def run(self, snapshot: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        decisions = list(snapshot.get("decisions") or [])
        existing_keys = set(snapshot.get("existing_execution_keys") or set())
        existing_entries = list(snapshot.get("existing_execution_entries") or [])

        execution_contexts = self._context_builder.build_all(snapshot)
        selection = self._selector.select(execution_contexts)
        mapping = self._mapper.map_all(decisions, execution_contexts, selection, snapshot)

        adapter_result = self._adapter.adapt(mapping, config)
        bridge_result = self._bridge.bridge(adapter_result, snapshot, mapping, config)

        self._registry_builder.set_sequence(int((snapshot.get("id_counters") or {}).get("execution") or 0))

        if existing_entries and existing_keys.issuperset(
            {f"EXEC::{item.get('decision_key')}" for item in decisions if item.get("decision_key")}
        ):
            registry = {
                "registry_count": len(existing_entries),
                "entries": existing_entries,
                "lifecycles": [
                    {
                        "execution_id": entry.get("execution_id"),
                        "decision_id": entry.get("decision_id"),
                        "lifecycle": entry.get("lifecycle"),
                        "valid_state": True,
                    }
                    for entry in existing_entries
                ],
                "new_execution_count": 0,
            }
            idempotent = True
            # Refresh lifecycle from current bridge without creating new IDs.
            refreshed = []
            for entry in existing_entries:
                updated = dict(entry)
                selected = next(
                    (item for item in selection if item.get("decision_id") == entry.get("decision_id")),
                    {},
                )
                updated["lifecycle"] = ExecutionRegistryBuilder._lifecycle_for(
                    selected,
                    bridge_result,
                    already_registered=True,
                )
                updated["execution_status"] = selected.get("execution_status", entry.get("execution_status"))
                updated["executable"] = bool(selected.get("executable"))
                refreshed.append(updated)
            registry["entries"] = sorted(refreshed, key=lambda item: str(item.get("execution_id") or ""))
            registry["lifecycles"] = [
                {
                    "execution_id": entry.get("execution_id"),
                    "decision_id": entry.get("decision_id"),
                    "lifecycle": entry.get("lifecycle"),
                    "valid_state": True,
                }
                for entry in registry["entries"]
            ]
        else:
            registry = self._registry_builder.build_all(
                decisions,
                execution_contexts,
                selection,
                mapping,
                existing_keys,
                bridge_result,
            )
            # Merge prior entries that are still valid.
            prior_by_key = {
                str(entry.get("execution_key")): entry
                for entry in existing_entries
                if entry.get("execution_key")
            }
            merged_entries = list(registry.get("entries") or [])
            for entry in merged_entries:
                key = str(entry.get("execution_key") or "")
                if key in prior_by_key and key in existing_keys:
                    # Prefer stable prior execution_id.
                    entry["execution_id"] = prior_by_key[key].get("execution_id") or entry.get("execution_id")
            registry["entries"] = sorted(merged_entries, key=lambda item: str(item.get("execution_id") or ""))
            registry["registry_count"] = len(registry["entries"])
            idempotent = False

        pipeline_steps = [
            {"step": "COLLECT_DECISIONS", "status": "PASS", "count": len(decisions)},
            {"step": "BUILD_EXECUTION_CONTEXT", "status": "PASS", "count": len(execution_contexts)},
            {"step": "SELECT_EXECUTABLE", "status": "PASS", "count": sum(1 for item in selection if item.get("executable"))},
            {"step": "MAP_TO_CALCULATION", "status": "PASS", "count": mapping.get("mapping_count", 0)},
            {
                "step": "CALCULATION_ADAPTER",
                "status": "PASS" if adapter_result.get("status") in {"SUCCESS", "SKIPPED", "DISABLED", "IDEMPOTENT_SKIP"} else "FAIL",
                "detail": adapter_result.get("status"),
            },
            {
                "step": "PRODUCTION_BRIDGE",
                "status": "PASS" if bridge_result.get("status") in {"SUCCESS", "SUCCESS_WITH_WARNINGS", "DISABLED"} else "FAIL",
                "detail": bridge_result.get("status"),
            },
            {"step": "EXECUTION_REGISTRY", "status": "PASS", "count": registry.get("registry_count", 0)},
        ]

        return {
            "execution_contexts": execution_contexts,
            "selection": selection,
            "mapping": mapping,
            "adapter_result": adapter_result,
            "bridge_result": bridge_result,
            "registry": registry,
            "pipeline_steps": pipeline_steps,
            "idempotent": idempotent,
        }
