"""Validate calculation readiness — Phase I.2.1."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement_calculation.calculation_state import (
    CalculationState,
    is_calculation_ready,
    parse_calculation_state,
)
from src.reinforcement_calculation.reinforcement_models import reinforcement_objects_applied
from src.reinforcement_calculation.reinforcement_registry import ReinforcementRegistry


class ReinforcementReadinessValidator:
    """Verify calculation readiness integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not reinforcement_objects_applied(model) and not model.get("reinforcement_groups"):
            return {
                "phase": "Phase I.2.1",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "reinforcement readiness not applied"},
            }

        bars = model.get("reinforcement_bars", [])
        groups = model.get("reinforcement_groups", [])
        registry = model.get("reinforcement_registry", {})

        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_bar_has_readiness(bars))
        checks.append(self._check_every_group_has_readiness(groups))
        checks.append(self._check_ready_objects_have_no_defer_reason(bars + groups))
        checks.append(self._check_deferred_objects_have_defer_reason(bars + groups))
        checks.append(self._check_boolean_matches_state(bars + groups))
        checks.append(self._check_no_unknown_state(bars + groups))
        checks.append(self._check_registry_readiness_counts(registry, bars))
        checks.append(self._check_bar_group_readiness_consistency(bars, groups))
        checks.append(self._check_group_bars_include_readiness(groups))
        checks.append(self._check_upstream_summary_present(bars + groups))
        checks.append(self._check_ready_bars_normalized(bars))
        checks.append(self._check_deferred_incomplete_contexts(model, bars))
        checks.append(self._check_registry_lookup_integrity(bars, groups))
        checks.append(self._check_export_readiness_records(model, bars, groups))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.2.1",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "bar_count": len(bars),
                "group_count": len(groups),
            },
        }

    @staticmethod
    def _readiness(record: dict[str, Any]) -> dict[str, Any]:
        value = record.get("calculation_readiness")
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _check_every_bar_has_readiness(bars: list) -> dict[str, Any]:
        missing = [
            item.get("bar_id")
            for item in bars
            if not ReinforcementReadinessValidator._readiness(item)
        ]
        return {
            "name": "Every Bar Has Readiness",
            "status": "PASS" if bars and not missing else "FAIL",
            "missing": missing[:10],
        }

    @staticmethod
    def _check_every_group_has_readiness(groups: list) -> dict[str, Any]:
        missing = [
            item.get("group_id")
            for item in groups
            if not ReinforcementReadinessValidator._readiness(item)
        ]
        return {
            "name": "Every Group Has Readiness",
            "status": "PASS" if groups and not missing else "FAIL",
            "missing": missing[:10],
        }

    @staticmethod
    def _check_ready_objects_have_no_defer_reason(records: list) -> dict[str, Any]:
        invalid = []
        for item in records:
            readiness = ReinforcementReadinessValidator._readiness(item)
            if readiness.get("calculation_state") == CalculationState.READY.value and readiness.get(
                "defer_reason"
            ):
                invalid.append(item.get("bar_id") or item.get("group_id"))
        return {
            "name": "READY Objects Have No Defer Reason",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_deferred_objects_have_defer_reason(records: list) -> dict[str, Any]:
        invalid = []
        for item in records:
            readiness = ReinforcementReadinessValidator._readiness(item)
            if readiness.get("calculation_state") == CalculationState.DEFERRED.value and not readiness.get(
                "defer_reason"
            ):
                invalid.append(item.get("bar_id") or item.get("group_id"))
        return {
            "name": "DEFERRED Objects Have Defer Reason",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_boolean_matches_state(records: list) -> dict[str, Any]:
        invalid = []
        for item in records:
            readiness = ReinforcementReadinessValidator._readiness(item)
            state = parse_calculation_state(readiness.get("calculation_state"))
            expected = is_calculation_ready(state)
            if readiness.get("calculation_ready") != expected:
                invalid.append(item.get("bar_id") or item.get("group_id"))
        return {
            "name": "Boolean Readiness Matches State",
            "status": "PASS" if records and not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_no_unknown_state(records: list) -> dict[str, Any]:
        invalid = [
            item.get("bar_id") or item.get("group_id")
            for item in records
            if ReinforcementReadinessValidator._readiness(item).get("calculation_state")
            == CalculationState.UNKNOWN.value
        ]
        return {
            "name": "No UNKNOWN State After Evaluation",
            "status": "PASS" if records and not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_registry_readiness_counts(registry: dict[str, Any], bars: list) -> dict[str, Any]:
        counts = registry.get("readiness_counts", {})
        ready = sum(
            1
            for bar in bars
            if ReinforcementReadinessValidator._readiness(bar).get("calculation_state")
            == CalculationState.READY.value
        )
        deferred = sum(
            1
            for bar in bars
            if ReinforcementReadinessValidator._readiness(bar).get("calculation_state")
            == CalculationState.DEFERRED.value
        )
        ok = (
            counts.get("ready") == ready
            and counts.get("deferred") == deferred
            and registry.get("bars_by_readiness", {}).get(CalculationState.READY.value, 0) == ready
        )
        return {
            "name": "Registry Readiness Counts Match Exported Objects",
            "status": "PASS" if bars and ok else "FAIL",
            "registry_ready": counts.get("ready"),
            "actual_ready": ready,
        }

    @staticmethod
    def _check_bar_group_readiness_consistency(bars: list, groups: list) -> dict[str, Any]:
        bar_map = {item.get("specification_id"): item for item in bars}
        invalid = []
        for group in groups:
            bar = bar_map.get(group.get("specification_id"))
            if not bar:
                invalid.append(group.get("group_id"))
                continue
            bar_state = ReinforcementReadinessValidator._readiness(bar).get("calculation_state")
            group_state = ReinforcementReadinessValidator._readiness(group).get("calculation_state")
            if bar_state != group_state:
                invalid.append(group.get("group_id"))
        return {
            "name": "Bar And Group Readiness Consistent",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_group_bars_include_readiness(groups: list) -> dict[str, Any]:
        invalid = []
        for group in groups:
            for bar in group.get("bars", []):
                if not ReinforcementReadinessValidator._readiness(bar):
                    invalid.append(group.get("group_id"))
                    break
        return {
            "name": "Group Bars Include Readiness",
            "status": "PASS" if groups and not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_upstream_summary_present(records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_id") or item.get("group_id")
            for item in records
            if not ReinforcementReadinessValidator._readiness(item).get("upstream_status_summary")
        ]
        return {
            "name": "Upstream Status Summary Present",
            "status": "PASS" if records and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_ready_bars_normalized(bars: list) -> dict[str, Any]:
        invalid = [
            item.get("bar_id")
            for item in bars
            if ReinforcementReadinessValidator._readiness(item).get("calculation_state")
            == CalculationState.READY.value
            and item.get("status") != "NORMALIZED"
        ]
        return {
            "name": "READY Bars Are Normalized",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_deferred_incomplete_contexts(model: dict[str, Any], bars: list) -> dict[str, Any]:
        contexts = {
            item.get("context_id"): item for item in model.get("calculation_contexts", [])
        }
        invalid = []
        for bar in bars:
            readiness = ReinforcementReadinessValidator._readiness(bar)
            context = contexts.get(bar.get("context_id"), {})
            if context.get("calculation_status") != "COMPLETE":
                if readiness.get("calculation_state") != CalculationState.DEFERRED.value:
                    invalid.append(bar.get("bar_id"))
        return {
            "name": "Incomplete Contexts Marked DEFERRED",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_registry_lookup_integrity(bars: list, groups: list) -> dict[str, Any]:
        lookup_registry = ReinforcementRegistry()
        for bar in bars:
            lookup_registry.register_bar(dict(bar))
        for group in groups:
            lookup_registry.register_group(dict(group))

        ok = (
            len(lookup_registry.get_ready_bars())
            == sum(
                1
                for bar in bars
                if ReinforcementReadinessValidator._readiness(bar).get("calculation_state")
                == CalculationState.READY.value
            )
            and len(lookup_registry.get_deferred_bars())
            == sum(
                1
                for bar in bars
                if ReinforcementReadinessValidator._readiness(bar).get("calculation_state")
                == CalculationState.DEFERRED.value
            )
            and len(lookup_registry.get_ready_groups()) == len(lookup_registry.get_ready_bars())
        )
        return {
            "name": "Registry Readiness Lookup Integrity",
            "status": "PASS" if bars and ok else "FAIL",
            "ready_bars": len(lookup_registry.get_ready_bars()),
        }

    @staticmethod
    def _check_export_readiness_records(
        model: dict[str, Any],
        bars: list,
        groups: list,
    ) -> dict[str, Any]:
        export = model.get("reinforcement_readiness", {})
        ok = (
            export.get("bar_count") == len(bars)
            and export.get("group_count") == len(groups)
            and len(export.get("bars", [])) == len(bars)
            and len(export.get("groups", [])) == len(groups)
        )
        return {
            "name": "Export Readiness Integrity",
            "status": "PASS" if bars and export and ok else "FAIL",
            "export_bar_count": export.get("bar_count"),
        }
