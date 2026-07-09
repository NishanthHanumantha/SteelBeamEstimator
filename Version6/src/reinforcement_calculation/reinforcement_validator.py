"""Validate reinforcement calculation objects — Phase I.2."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement_calculation.reinforcement_models import reinforcement_objects_applied
from src.reinforcement_calculation.reinforcement_registry import ReinforcementRegistry
from src.reinforcement_calculation.reinforcement_types import (
    VALID_BAR_STATUSES,
    VALID_BAR_TYPES,
    VALID_ENGINEERING_ROLES,
)


class ReinforcementValidator:
    """Verify reinforcement normalization integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not reinforcement_objects_applied(model) and not model.get("reinforcement_groups"):
            return {
                "phase": "Phase I.2",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "reinforcement calculation not applied"},
            }

        contexts = model.get("calculation_contexts", [])
        specifications = model.get("engineering_specifications", [])
        bars = model.get("reinforcement_bars", [])
        groups = model.get("reinforcement_groups", [])
        registry = model.get("reinforcement_registry", {})

        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_context_has_reinforcement(contexts, registry))
        checks.append(self._check_every_specification_has_group(specifications, groups))
        checks.append(self._check_quantity_positive(bars))
        checks.append(self._check_diameter_positive(bars))
        checks.append(self._check_role_resolved(bars))
        checks.append(self._check_steel_grade_resolved(bars))
        checks.append(self._check_supported_roles(bars))
        checks.append(self._check_supported_bar_types(bars))
        checks.append(self._check_unique_bar_ids(bars))
        checks.append(self._check_unique_group_ids(groups))
        checks.append(self._check_registry_integrity(registry, bars, groups, contexts))
        checks.append(self._check_deterministic_bar_ids(bars))
        checks.append(self._check_specification_references_preserved(bars, specifications))
        checks.append(self._check_context_references_preserved(bars, contexts))
        checks.append(self._check_no_duplicate_specification_mapping(bars))
        checks.append(self._check_immutable_bar_structure(bars))
        checks.append(self._check_immutable_group_structure(groups))
        checks.append(self._check_no_length_calculations(bars, groups))
        checks.append(self._check_group_bar_consistency(groups, bars))
        checks.append(self._check_registry_lookup_integrity(bars, groups))
        checks.append(self._check_export_consistency(model, bars, groups))
        checks.append(self._check_traceability_preserved(bars))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.2",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "context_count": len(contexts),
                "bar_count": len(bars),
                "group_count": len(groups),
            },
        }

    @staticmethod
    def _check_every_context_has_reinforcement(
        contexts: list,
        registry: dict[str, Any],
    ) -> dict[str, Any]:
        context_ids = {item.get("context_id") for item in contexts if item.get("context_id")}
        processed = set(registry.get("processed_context_ids", []))
        missing = sorted(context_ids - processed)
        return {
            "name": "Every Context Has Reinforcement Object",
            "status": "PASS" if contexts and not missing else "FAIL",
            "missing": missing[:10],
            "processed_count": len(processed),
            "context_count": len(context_ids),
        }

    @staticmethod
    def _check_every_specification_has_group(
        specifications: list,
        groups: list,
    ) -> dict[str, Any]:
        spec_ids = {item.get("specification_id") for item in specifications}
        group_spec_ids = {item.get("specification_id") for item in groups}
        missing = sorted(spec_ids - group_spec_ids)
        return {
            "name": "Every Specification Has Reinforcement Group",
            "status": "PASS" if specifications and not missing else "FAIL",
            "missing": missing[:10],
            "specification_count": len(spec_ids),
        }

    @staticmethod
    def _check_quantity_positive(bars: list) -> dict[str, Any]:
        invalid = [
            item.get("bar_id")
            for item in bars
            if item.get("status") == "NORMALIZED"
            and not (isinstance(item.get("quantity"), int) and item.get("quantity", 0) > 0)
        ]
        return {
            "name": "Quantity Greater Than Zero",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_diameter_positive(bars: list) -> dict[str, Any]:
        invalid = [
            item.get("bar_id")
            for item in bars
            if item.get("status") == "NORMALIZED"
            and not (
                isinstance(item.get("diameter_mm"), (int, float))
                and float(item.get("diameter_mm", 0)) > 0
            )
        ]
        return {
            "name": "Diameter Greater Than Zero",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_role_resolved(bars: list) -> dict[str, Any]:
        invalid = [
            item.get("bar_id")
            for item in bars
            if item.get("status") == "NORMALIZED" and item.get("role") in (None, "", "UNKNOWN")
        ]
        return {
            "name": "Role Resolved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_steel_grade_resolved(bars: list) -> dict[str, Any]:
        invalid = [
            item.get("bar_id") for item in bars if item.get("status") == "NORMALIZED" and not item.get("steel_grade")
        ]
        return {
            "name": "Steel Grade Resolved",
            "status": "PASS" if bars and not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_supported_roles(bars: list) -> dict[str, Any]:
        invalid = [
            item.get("bar_id")
            for item in bars
            if item.get("role") not in VALID_ENGINEERING_ROLES
        ]
        return {
            "name": "Supported Role",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_supported_bar_types(bars: list) -> dict[str, Any]:
        invalid = [
            item.get("bar_id")
            for item in bars
            if item.get("bar_type") not in VALID_BAR_TYPES
        ]
        return {
            "name": "Supported Bar Type",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_unique_bar_ids(bars: list) -> dict[str, Any]:
        ids = [item.get("bar_id") for item in bars]
        return {
            "name": "No Duplicate Bar IDs",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
            "bar_count": len(ids),
        }

    @staticmethod
    def _check_unique_group_ids(groups: list) -> dict[str, Any]:
        ids = [item.get("group_id") for item in groups]
        return {
            "name": "No Duplicate Group IDs",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
            "group_count": len(ids),
        }

    @staticmethod
    def _check_registry_integrity(
        registry: dict[str, Any],
        bars: list,
        groups: list,
        contexts: list,
    ) -> dict[str, Any]:
        ok = (
            registry.get("bar_count") == len(bars)
            and registry.get("group_count") == len(groups)
            and registry.get("context_count") == len(contexts)
            and registry.get("namespace") == "REBAR"
            and len(registry.get("processed_context_ids", [])) == len(contexts)
        )
        return {
            "name": "Registry Integrity",
            "status": "PASS" if bars and groups and ok else "FAIL",
            "registry_bar_count": registry.get("bar_count"),
            "actual_bar_count": len(bars),
        }

    @staticmethod
    def _check_deterministic_bar_ids(bars: list) -> dict[str, Any]:
        invalid = [
            item.get("bar_id")
            for item in bars
            if not str(item.get("bar_id", "")).startswith("REBAR::")
        ]
        return {
            "name": "Deterministic IDs",
            "status": "PASS" if bars and not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_specification_references_preserved(
        bars: list,
        specifications: list,
    ) -> dict[str, Any]:
        spec_beams = {item.get("specification_id"): item.get("beam_id") for item in specifications}
        invalid = [
            item.get("bar_id")
            for item in bars
            if spec_beams.get(item.get("specification_id")) != item.get("beam_id")
        ]
        return {
            "name": "Specification References Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_context_references_preserved(
        bars: list,
        contexts: list,
    ) -> dict[str, Any]:
        context_map = {item.get("context_id"): item for item in contexts}
        invalid = [
            item.get("bar_id")
            for item in bars
            if context_map.get(item.get("context_id"), {}).get("specification_id")
            != item.get("specification_id")
        ]
        return {
            "name": "Calculation Context References Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_no_duplicate_specification_mapping(bars: list) -> dict[str, Any]:
        spec_ids = [item.get("specification_id") for item in bars]
        return {
            "name": "One Bar Per Specification",
            "status": "PASS" if len(spec_ids) == len(set(spec_ids)) else "FAIL",
            "bar_count": len(spec_ids),
        }

    @staticmethod
    def _check_immutable_bar_structure(bars: list) -> dict[str, Any]:
        forbidden = {
            "beams",
            "length_model",
            "development_length",
            "cut_length",
            "weight_kg",
            "resolved_properties",
        }
        invalid = [
            item.get("bar_id")
            for item in bars
            if forbidden.intersection(item.keys())
            or item.get("status") not in VALID_BAR_STATUSES
        ]
        return {
            "name": "Immutable Bar Structure",
            "status": "PASS" if bars and not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_immutable_group_structure(groups: list) -> dict[str, Any]:
        invalid = [
            item.get("group_id")
            for item in groups
            if not isinstance(item.get("bars"), list) or not item.get("bars")
        ]
        return {
            "name": "Immutable Group Structure",
            "status": "PASS" if groups and not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_no_length_calculations(bars: list, groups: list) -> dict[str, Any]:
        forbidden = {
            "development_length_mm",
            "lap_length_mm",
            "hook_length_mm",
            "cut_length_mm",
            "bar_length_mm",
            "weight_kg",
            "steel_quantity",
        }
        invalid: List[str] = []
        for item in bars + groups:
            if forbidden.intersection(item.keys()):
                invalid.append(item.get("bar_id") or item.get("group_id"))
        return {
            "name": "No Length Calculations",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_group_bar_consistency(groups: list, bars: list) -> dict[str, Any]:
        bar_map = {item.get("bar_id"): item for item in bars}
        invalid = []
        for group in groups:
            group_bars = group.get("bars", [])
            if len(group_bars) != 1:
                invalid.append(group.get("group_id"))
                continue
            bar = group_bars[0]
            if bar.get("bar_id") not in bar_map:
                invalid.append(group.get("group_id"))
        return {
            "name": "Group Bar Consistency",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_registry_lookup_integrity(
        bars: list,
        groups: list,
    ) -> dict[str, Any]:
        lookup_registry = ReinforcementRegistry()
        for bar in bars:
            lookup_registry.register_bar(dict(bar))
        for group in groups:
            lookup_registry.register_group(dict(group))

        ok = True
        for bar in bars:
            spec_id = str(bar.get("specification_id", ""))
            if lookup_registry.bar_by_specification(spec_id) is None:
                ok = False
                break

        return {
            "name": "Registry Lookup Integrity",
            "status": "PASS" if bars and ok else "FAIL",
            "bar_count": len(bars),
        }

    @staticmethod
    def _check_export_consistency(
        model: dict[str, Any],
        bars: list,
        groups: list,
    ) -> dict[str, Any]:
        registry = model.get("reinforcement_registry", {})
        ok = (
            registry.get("bar_count") == len(bars)
            and registry.get("group_count") == len(groups)
            and set(registry.get("bar_ids", [])) == {item.get("bar_id") for item in bars}
            and set(registry.get("group_ids", [])) == {item.get("group_id") for item in groups}
        )
        return {
            "name": "Export Integrity",
            "status": "PASS" if bars and groups and ok else "FAIL",
            "bar_count": len(bars),
        }

    @staticmethod
    def _check_traceability_preserved(bars: list) -> dict[str, Any]:
        missing = [
            item.get("bar_id")
            for item in bars
            if not (item.get("traceability") or {}).get("lineage")
        ]
        return {
            "name": "Traceability Preserved",
            "status": "PASS" if bars and not missing else "FAIL",
            "missing_count": len(missing),
        }
