"""Reporting helpers for Phase K.2."""

from __future__ import annotations

from typing import Any, Dict

from decision_collector import MODEL_VERSION, PHASE


class ExecutionReporting:
    """Build report payloads."""

    @staticmethod
    def build_report(result: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "run_timestamp": result.get("run_timestamp"),
            "statistics": result.get("statistics"),
            "health": result.get("health"),
            "summary": result.get("summary"),
            "adapter_result": result.get("adapter_result"),
            "production_bridge": result.get("production_bridge"),
            "validation_status": (result.get("validation") or {}).get("status"),
            "pipeline_steps": result.get("pipeline_steps"),
            "idempotent": result.get("idempotent"),
        }

    @staticmethod
    def build_traceability(
        registry_entries: list[dict[str, Any]],
        decisions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        decision_by_id = {
            str(item.get("decision_id")): item for item in decisions if item.get("decision_id")
        }
        chains = []
        for entry in registry_entries:
            decision = decision_by_id.get(str(entry.get("decision_id")) or "") or {}
            chains.append(
                {
                    "execution_id": entry.get("execution_id"),
                    "decision_id": entry.get("decision_id"),
                    "lineage": [
                        "Drawing",
                        "Engineering Object",
                        "Recovered Object",
                        "Engineering Intent",
                        "Engineering Decision",
                        "Execution Registry",
                        "Calculation",
                        "Steel",
                        "BBS",
                        "Excel",
                        "QA",
                        "Production Snapshot",
                    ],
                    "engineering_object_id": entry.get("engineering_object_id")
                    or decision.get("engineering_object_id"),
                    "source_bar_id": entry.get("source_bar_id") or decision.get("source_bar_id"),
                    "primary_intent_id": entry.get("primary_intent_id")
                    or (decision.get("primary_intent") or {}).get("intent_id"),
                    "beam_id": entry.get("beam_id") or decision.get("beam_id"),
                    "lifecycle": entry.get("lifecycle"),
                    "execution_status": entry.get("execution_status"),
                }
            )
        return sorted(chains, key=lambda item: str(item.get("execution_id") or ""))
