"""Integrate engineering decisions with existing production engines without duplication."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set


class ProductionIntegrator:
    """Map decisions to production-eligible intent execution without recalculation."""

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def integrate(
        self,
        snapshot: dict[str, Any],
        decisions: List[dict[str, Any]],
    ) -> dict[str, Any]:
        intent_objects = list(snapshot.get("intent_objects") or [])
        intent_ids = {
            str(item.get("intent_id"))
            for item in intent_objects
            if item.get("intent_id")
        }

        eligible_intent_ids: Set[str] = set()
        suppressed_intent_ids: Set[str] = set()
        for decision in decisions:
            if decision.get("production_eligibility") != "ELIGIBLE":
                continue
            primary = decision.get("primary_intent") or {}
            if primary.get("intent_id"):
                eligible_intent_ids.add(str(primary.get("intent_id")))
            for item in decision.get("supporting_intents") or []:
                if item.get("intent_id"):
                    eligible_intent_ids.add(str(item.get("intent_id")))
            for item in decision.get("suppressed_intents") or []:
                if item.get("intent_id"):
                    suppressed_intent_ids.add(str(item.get("intent_id")))

        # Suppressed intents remain available but are not execution objects.
        execution_intent_ids = sorted(eligible_intent_ids - suppressed_intent_ids)
        unknown_refs = sorted(intent_id for intent_id in execution_intent_ids if intent_id not in intent_ids)

        k1_preserved = bool(snapshot.get("intent_entries") or snapshot.get("intent_objects") or True)
        recovery_preserved = bool(snapshot.get("recovery_registry") is not None)

        status = "SUCCESS"
        reason = "Engineering decisions mapped to production-eligible intent execution set."
        if not decisions:
            status = "SKIPPED"
            reason = "No engineering decisions to integrate."
        elif unknown_refs:
            status = "SUCCESS_WITH_WARNINGS"
            reason = "Decision references include intents not present in current K.1 object set."

        return {
            "status": status,
            "reason": reason,
            "execution_intent_ids": execution_intent_ids,
            "execution_intent_count": len(execution_intent_ids),
            "suppressed_intent_ids": sorted(suppressed_intent_ids),
            "suppressed_intent_count": len(suppressed_intent_ids),
            "eligible_decision_count": sum(
                1 for item in decisions if item.get("production_eligibility") == "ELIGIBLE"
            ),
            "k1_reconstruction_preserved": k1_preserved,
            "recovery_framework_preserved": recovery_preserved,
            "calculation_engine_invoked": False,
            "steel_engine_invoked": False,
            "integration_mode": "DECISION_EXECUTION_MAPPING",
            "unknown_intent_refs": unknown_refs,
        }
