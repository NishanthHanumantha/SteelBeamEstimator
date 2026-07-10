"""Build and maintain the Engineering Decision Execution Registry."""

from __future__ import annotations

from typing import Any, Dict, List, Set


LIFECYCLE_STATES = (
    "CREATED",
    "VALIDATED",
    "READY",
    "EXECUTING",
    "CALCULATED",
    "STEEL_COMPLETE",
    "BBS_COMPLETE",
    "EXCEL_COMPLETE",
    "QA_VISIBLE",
    "FAILED",
    "DEFERRED",
    "BLOCKED",
)


class ExecutionRegistryBuilder:
    """Create one execution registry entry per Engineering Decision."""

    def __init__(self) -> None:
        self._sequence = 0

    def set_sequence(self, start: int) -> None:
        self._sequence = int(start)

    def build_all(
        self,
        decisions: List[dict[str, Any]],
        execution_contexts: List[dict[str, Any]],
        selection: List[dict[str, Any]],
        mapping: dict[str, Any],
        existing_keys: Set[str],
        bridge_result: dict[str, Any],
    ) -> dict[str, Any]:
        context_by_id = {
            str(item.get("decision_id")): item for item in execution_contexts if item.get("decision_id")
        }
        selection_by_id = {
            str(item.get("decision_id")): item for item in selection if item.get("decision_id")
        }
        mapping_by_id = {
            str(item.get("decision_id")): item
            for item in (mapping.get("mappings") or [])
            if item.get("decision_id")
        }

        entries: List[dict[str, Any]] = []
        lifecycles: List[dict[str, Any]] = []
        new_entries: List[dict[str, Any]] = []

        for decision in decisions:
            decision_id = str(decision.get("decision_id") or "")
            execution_key = f"EXEC::{decision.get('decision_key') or decision_id}"
            selected = selection_by_id.get(decision_id) or {}
            context = context_by_id.get(decision_id) or {}
            mapped = mapping_by_id.get(decision_id) or {}

            lifecycle = self._lifecycle_for(
                selected,
                bridge_result,
                already_registered=execution_key in existing_keys,
            )
            if execution_key in existing_keys:
                # Keep stable IDs for idempotent runs by synthesizing from decision id sequence.
                execution_id = f"EXEC::{decision_id.split('::')[-1]}" if "::" in decision_id else f"EXEC::{decision_id}"
            else:
                self._sequence += 1
                execution_id = f"EXEC::{self._sequence:06d}"
                new_entries.append(decision_id)

            entry = {
                "execution_id": execution_id,
                "execution_key": execution_key,
                "decision_id": decision_id,
                "decision_key": decision.get("decision_key"),
                "execution_source": "ENGINEERING_DECISION",
                "calculation_target": "phase_i/i_2_2_calculation_result_framework",
                "steel_target": "phase_i/i_11_steel_weight",
                "bbs_target": "phase_i/i_10_bbs",
                "excel_target": "phase_i/i_17_excel_export",
                "execution_status": selected.get("execution_status", "NOT_EXECUTABLE"),
                "lifecycle": lifecycle,
                "executable": bool(selected.get("executable")),
                "beam_id": decision.get("beam_id"),
                "source_bar_id": decision.get("source_bar_id"),
                "engineering_object_id": decision.get("engineering_object_id"),
                "primary_intent_id": (decision.get("primary_intent") or {}).get("intent_id"),
                "decision_category": decision.get("decision_category"),
                "traceability": {
                    "decision_id": decision_id,
                    "engineering_object_id": decision.get("engineering_object_id"),
                    "source_bar_id": decision.get("source_bar_id"),
                    "primary_intent_id": (decision.get("primary_intent") or {}).get("intent_id"),
                    "calculation_context_id": (context.get("calculation_context") or {}).get("context_id"),
                },
                "calculation_input": mapped.get("calculation_input"),
                "production_targets": mapped.get("production_targets"),
            }
            entries.append(entry)
            lifecycles.append(
                {
                    "execution_id": execution_id,
                    "decision_id": decision_id,
                    "lifecycle": lifecycle,
                    "valid_state": lifecycle in LIFECYCLE_STATES,
                }
            )

        return {
            "registry_count": len(entries),
            "entries": sorted(entries, key=lambda item: str(item.get("execution_id") or "")),
            "lifecycles": sorted(lifecycles, key=lambda item: str(item.get("execution_id") or "")),
            "new_execution_count": len(new_entries),
        }

    @staticmethod
    def _lifecycle_for(
        selected: dict[str, Any],
        bridge_result: dict[str, Any],
        *,
        already_registered: bool,
    ) -> str:
        if not selected.get("executable"):
            return "BLOCKED" if selected.get("failed_checks") else "DEFERRED"
        bridge_status = str(bridge_result.get("status") or "")
        if bridge_status in {"SUCCESS", "IDEMPOTENT_SKIP"}:
            if bridge_result.get("excel_complete"):
                return "EXCEL_COMPLETE"
            if bridge_result.get("bbs_complete"):
                return "BBS_COMPLETE"
            if bridge_result.get("steel_complete"):
                return "STEEL_COMPLETE"
            if bridge_result.get("calculation_complete"):
                return "CALCULATED"
            return "READY" if already_registered else "CALCULATED"
        if bridge_status == "DISABLED":
            return "DEFERRED"
        if bridge_status == "FAILED":
            return "FAILED"
        return "READY"
