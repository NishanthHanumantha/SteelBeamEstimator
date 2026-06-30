"""Validate Phase G.4.1 ERC lifecycle scaffolding."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement.engineering_asset_registry import engineering_assets_applied
from src.reinforcement.engineering_reinforcement_state_machine import (
    STATE_OWNERSHIP_READY,
    EngineeringReinforcementLifecycle,
    VALID_STATES,
    format_erc_lifecycle_id,
)


class EngineeringReinforcementLifecycleValidator:
    """Verify lifecycle metadata on every ERC."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not engineering_assets_applied(model):
            return {
                "phase": "Phase G.4.1",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "engineering_asset_registry not applied"},
            }

        contexts = model.get("engineering_reinforcement_contexts", [])
        lifecycle_registry = model.get("engineering_reinforcement_lifecycle_registry", {})
        checks: List[dict[str, Any]] = []
        checks.append(self._check_lifecycle_exists(contexts))
        checks.append(self._check_lifecycle_state_valid(contexts))
        checks.append(self._check_current_state_ownership_ready(contexts))
        checks.append(self._check_next_allowed(contexts))
        checks.append(self._check_lifecycle_registry(contexts, lifecycle_registry))
        checks.append(self._check_no_parsing_started(contexts))
        checks.append(self._check_no_quantities(contexts))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.4.1",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "context_count": len(contexts),
            },
        }

    def _check_lifecycle_exists(self, contexts: list) -> dict[str, Any]:
        missing = [
            c.get("reinforcement_context_id")
            for c in contexts
            if "lifecycle" not in c
        ]
        return {
            "name": "Lifecycle Exists",
            "status": "PASS" if contexts and not missing else "FAIL",
            "missing": missing,
        }

    def _check_lifecycle_state_valid(self, contexts: list) -> dict[str, Any]:
        invalid = []
        for ctx in contexts:
            state = ctx.get("lifecycle", {}).get("current_state")
            if state not in VALID_STATES:
                invalid.append(ctx.get("reinforcement_context_id"))
        return {
            "name": "Lifecycle State Valid",
            "status": "PASS" if contexts and not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_current_state_ownership_ready(self, contexts: list) -> dict[str, Any]:
        invalid = [
            c.get("reinforcement_context_id")
            for c in contexts
            if c.get("lifecycle", {}).get("current_state") != STATE_OWNERSHIP_READY
        ]
        return {
            "name": "Current State OWNERSHIP_READY",
            "status": "PASS" if contexts and not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_next_allowed(self, contexts: list) -> dict[str, Any]:
        invalid = []
        for ctx in contexts:
            lifecycle = ctx.get("lifecycle", {})
            state = lifecycle.get("current_state", "")
            expected = EngineeringReinforcementLifecycle.next_allowed(state)
            if list(lifecycle.get("next_allowed", [])) != expected:
                invalid.append(ctx.get("reinforcement_context_id"))
        return {
            "name": "Next Allowed Transitions",
            "status": "PASS" if contexts and not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_lifecycle_registry(
        self,
        contexts: list,
        lifecycle_registry: dict[str, Any],
    ) -> dict[str, Any]:
        entries = lifecycle_registry.get("ercs", [])
        if len(entries) != len(contexts):
            return {
                "name": "Lifecycle Registry Complete",
                "status": "FAIL",
                "expected": len(contexts),
                "actual": len(entries),
            }
        if lifecycle_registry.get("current_state") != STATE_OWNERSHIP_READY:
            return {
                "name": "Lifecycle Registry Complete",
                "status": "FAIL",
                "reason": "registry current_state",
            }
        invalid = []
        for entry in entries:
            beam_mark = str(entry.get("beam_mark", ""))
            if entry.get("lifecycle_id") != format_erc_lifecycle_id(beam_mark):
                invalid.append(entry.get("reinforcement_context_id"))
        return {
            "name": "Lifecycle Registry Complete",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_no_parsing_started(self, contexts: list) -> dict[str, Any]:
        invalid = []
        for ctx in contexts:
            results = ctx.get("engineering_results", {})
            if results.get("parsed_reinforcement") is not None:
                invalid.append(ctx.get("reinforcement_context_id"))
            if results.get("bar_objects") is not None:
                invalid.append(ctx.get("reinforcement_context_id"))
        return {
            "name": "No Parsing Started",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_no_quantities(self, contexts: list) -> dict[str, Any]:
        invalid = []
        for ctx in contexts:
            results = ctx.get("engineering_results", {})
            for key in ("steel_quantities", "concrete_quantities", "boq"):
                if results.get(key) is not None:
                    invalid.append(ctx.get("reinforcement_context_id"))
        return {
            "name": "No Quantities Computed",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }
