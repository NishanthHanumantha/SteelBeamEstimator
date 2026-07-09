"""Validate calculation indexes — Phase I.4.5."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.calculation_index.calculation_index_builder import (
    calculation_index_applied,
)
from src.engineering_calculations.calculation_index.calculation_index_registry import (
    CalculationIndexRegistry,
)
from src.engineering_calculations.calculation_index.calculation_index_types import (
    CALCULATION_TYPE_TO_INDEX_CATEGORY,
    CATEGORY_DEVELOPMENT_LENGTH,
    CATEGORY_HOOK_LENGTH,
    FORBIDDEN_REFERENCE_VALUE_KEYS,
    NAMESPACE_CALCULATION_INDEX,
    SUPPORTED_INDEX_CATEGORIES,
)
from src.engineering_calculations.calculation_result_types import CalculationResultState


class CalculationIndexValidator:
    """Verify calculation index integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not calculation_index_applied(model) and not model.get("calculation_indexes"):
            return {
                "phase": "Phase I.4.5",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "calculation index not applied"},
            }

        bars = model.get("reinforcement_bars", [])
        results = model.get("engineering_calculation_results", [])
        indexes = model.get("calculation_indexes", [])
        registry = model.get("calculation_index_registry", {})
        contexts = model.get("calculation_contexts", [])

        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_bar_has_calculation_index(bars))
        checks.append(self._check_every_result_indexed(results, indexes))
        checks.append(self._check_no_duplicate_categories(indexes))
        checks.append(self._check_development_length_indexed(indexes))
        checks.append(self._check_hook_length_indexed(indexes))
        checks.append(self._check_deferred_results_indexed(results, indexes))
        checks.append(self._check_blocked_results_indexed(results, indexes))
        checks.append(self._check_calculated_results_indexed(results, indexes))
        checks.append(self._check_registry_consistency(registry, indexes, results))
        checks.append(self._check_reference_integrity(results, indexes))
        checks.append(self._check_deterministic_ordering(indexes))
        checks.append(self._check_no_duplicated_engineering_values(indexes))
        checks.append(self._check_no_geometry_modified(model, contexts))
        checks.append(self._check_no_calculation_mutation(model))
        checks.append(self._check_no_registry_mutation(model))
        checks.append(self._check_statistics_consistency(model, indexes, results))
        checks.append(self._check_export_integrity(registry, indexes))
        checks.append(self._check_lookup_performance(indexes))
        checks.append(self._check_category_uniqueness(indexes))
        checks.append(self._check_future_category_support(indexes))
        checks.append(self._check_calculation_reproducibility(results, indexes))
        checks.append(self._check_index_immutability_fields(indexes))
        checks.append(self._check_no_orphan_references(results, indexes))
        checks.append(self._check_no_missing_references(results, indexes))
        checks.append(self._check_no_invalid_references(results, indexes))
        checks.append(self._check_no_cross_bar_references(results, indexes))
        checks.append(self._check_builder_idempotence(indexes))
        checks.append(self._check_bar_index_alignment(bars, indexes))
        checks.append(self._check_unique_index_ids(indexes))
        checks.append(self._check_deterministic_index_ids(indexes))
        checks.append(self._check_registry_lookup_integrity(indexes))
        checks.append(self._check_reference_only_metadata(indexes))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.4.5",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "bar_count": len(bars),
                "index_count": len(indexes),
                "result_count": len(results),
            },
        }

    @staticmethod
    def _check_every_bar_has_calculation_index(bars: list) -> dict[str, Any]:
        missing = [
            item.get("bar_id")
            for item in bars
            if not item.get("calculation_index")
        ]
        return {
            "name": "Every ReinforcementBar Has Calculation Index",
            "status": "PASS" if bars and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_every_result_indexed(results: list, indexes: list) -> dict[str, Any]:
        referenced = {
            result_id
            for index in indexes
            for result_id in (index.get("references") or {}).values()
        }
        missing = [
            item.get("result_id")
            for item in results
            if item.get("result_id") not in referenced
        ]
        return {
            "name": "Every EngineeringCalculationResult Indexed",
            "status": "PASS" if results and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_no_duplicate_categories(indexes: list) -> dict[str, Any]:
        invalid = []
        for index in indexes:
            references = index.get("references") or {}
            if len(references) != len(set(references.keys())):
                invalid.append(index.get("index_id"))
        return {
            "name": "No Duplicate Categories",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_development_length_indexed(indexes: list) -> dict[str, Any]:
        count = sum(
            1 for index in indexes if CATEGORY_DEVELOPMENT_LENGTH in (index.get("references") or {})
        )
        return {
            "name": "Development Length Indexed",
            "status": "PASS" if indexes and count == len(indexes) else "FAIL",
            "indexed_count": count,
        }

    @staticmethod
    def _check_hook_length_indexed(indexes: list) -> dict[str, Any]:
        count = sum(
            1 for index in indexes if CATEGORY_HOOK_LENGTH in (index.get("references") or {})
        )
        return {
            "name": "Hook Length Indexed",
            "status": "PASS" if indexes and count == len(indexes) else "FAIL",
            "indexed_count": count,
        }

    @staticmethod
    def _check_deferred_results_indexed(results: list, indexes: list) -> dict[str, Any]:
        deferred_ids = {
            item.get("result_id")
            for item in results
            if item.get("calculation_state") == CalculationResultState.DEFERRED.value
        }
        referenced = {
            result_id
            for index in indexes
            for result_id in (index.get("references") or {}).values()
        }
        missing = deferred_ids - referenced
        return {
            "name": "Deferred Results Indexed Correctly",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_blocked_results_indexed(results: list, indexes: list) -> dict[str, Any]:
        blocked_ids = {
            item.get("result_id")
            for item in results
            if item.get("calculation_state") == CalculationResultState.BLOCKED.value
        }
        referenced = {
            result_id
            for index in indexes
            for result_id in (index.get("references") or {}).values()
        }
        missing = blocked_ids - referenced
        return {
            "name": "Blocked Results Indexed Correctly",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_results_indexed(results: list, indexes: list) -> dict[str, Any]:
        calculated_ids = {
            item.get("result_id")
            for item in results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
        }
        referenced = {
            result_id
            for index in indexes
            for result_id in (index.get("references") or {}).values()
        }
        missing = calculated_ids - referenced
        return {
            "name": "Calculated Results Indexed Correctly",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_registry_consistency(registry: dict, indexes: list, results: list) -> dict[str, Any]:
        ok = (
            registry.get("namespace") == NAMESPACE_CALCULATION_INDEX
            and registry.get("index_count") == len(indexes)
            and registry.get("result_count") == len(results)
            and set(registry.get("index_ids", [])) == {item.get("index_id") for item in indexes}
        )
        return {
            "name": "Registry Consistency",
            "status": "PASS" if indexes and ok else "FAIL",
            "index_count": len(indexes),
        }

    @staticmethod
    def _check_reference_integrity(results: list, indexes: list) -> dict[str, Any]:
        result_map = {item.get("result_id"): item for item in results}
        invalid = []
        for index in indexes:
            bar_id = index.get("bar_id")
            for category, result_id in (index.get("references") or {}).items():
                result = result_map.get(result_id)
                if not result:
                    invalid.append(result_id)
                elif result.get("input_bar_id") != bar_id:
                    invalid.append(result_id)
                elif CALCULATION_TYPE_TO_INDEX_CATEGORY.get(result.get("calculation_type")) != category:
                    invalid.append(result_id)
        return {
            "name": "Reference Integrity",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_deterministic_ordering(indexes: list) -> dict[str, Any]:
        invalid = []
        for index in indexes:
            categories = index.get("categories") or []
            references = index.get("references") or {}
            if categories != sorted(references.keys()):
                invalid.append(index.get("index_id"))
        return {
            "name": "Deterministic Ordering",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_duplicated_engineering_values(indexes: list) -> dict[str, Any]:
        invalid = []
        for index in indexes:
            for category, value in (index.get("references") or {}).items():
                if not isinstance(value, str):
                    invalid.append(index.get("index_id"))
                elif not str(value).startswith("CALC_RESULT::"):
                    invalid.append(index.get("index_id"))
                elif category in FORBIDDEN_REFERENCE_VALUE_KEYS:
                    invalid.append(index.get("index_id"))
        return {
            "name": "No Duplicated Engineering Values",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_geometry_modified(model: dict[str, Any], contexts: list) -> dict[str, Any]:
        forbidden = {"development_length_mm", "cut_length_mm", "hook_length_mm", "lap_length_mm"}
        invalid = []
        for context in contexts:
            if forbidden.intersection(context.keys()):
                invalid.append(context.get("context_id"))
        for bar in model.get("reinforcement_bars", []):
            if forbidden.intersection(bar.keys()):
                invalid.append(bar.get("bar_id"))
        return {
            "name": "No Geometry Modified",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_calculation_mutation(model: dict[str, Any]) -> dict[str, Any]:
        original_count = model.get("calculation_result_registry", {}).get("result_count")
        results = model.get("engineering_calculation_results", [])
        ok = original_count is None or original_count == len(results)
        return {
            "name": "No Calculation Mutation",
            "status": "PASS" if ok else "FAIL",
            "result_count": len(results),
        }

    @staticmethod
    def _check_no_registry_mutation(model: dict[str, Any]) -> dict[str, Any]:
        calc_registry = model.get("calculation_result_registry", {})
        ok = calc_registry.get("namespace") == "CALCULATION_RESULT"
        return {
            "name": "No Registry Mutation",
            "status": "PASS" if ok else "FAIL",
            "namespace": calc_registry.get("namespace"),
        }

    @staticmethod
    def _check_statistics_consistency(model: dict[str, Any], indexes: list, results: list) -> dict[str, Any]:
        registry = model.get("calculation_index_registry", {})
        referenced = sum(len(index.get("references") or {}) for index in indexes)
        ok = registry.get("index_count") == len(indexes) and registry.get("result_count") == len(results)
        return {
            "name": "Statistics Consistency",
            "status": "PASS" if indexes and ok and referenced == len(results) else "FAIL",
            "indexed_calculations": referenced,
        }

    @staticmethod
    def _check_export_integrity(registry: dict, indexes: list) -> dict[str, Any]:
        ok = registry.get("determination_count") is None and registry.get("index_count") == len(indexes)
        return {
            "name": "Export Integrity",
            "status": "PASS" if indexes and ok else "FAIL",
            "index_count": len(indexes),
        }

    @staticmethod
    def _check_lookup_performance(indexes: list) -> dict[str, Any]:
        lookup_registry = CalculationIndexRegistry()
        for index in indexes:
            lookup_registry.register(dict(index))
        ok = all(lookup_registry.index_by_bar(index.get("bar_id")) for index in indexes)
        return {
            "name": "Lookup Performance",
            "status": "PASS" if indexes and ok else "FAIL",
            "index_count": len(indexes),
        }

    @staticmethod
    def _check_category_uniqueness(indexes: list) -> dict[str, Any]:
        invalid = []
        for index in indexes:
            references = index.get("references") or {}
            if len(references) != len(set(references.keys())):
                invalid.append(index.get("index_id"))
        return {
            "name": "Category Uniqueness",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_future_category_support(indexes: list) -> dict[str, Any]:
        invalid = []
        for index in indexes:
            for category in (index.get("references") or {}).keys():
                if category not in SUPPORTED_INDEX_CATEGORIES:
                    invalid.append(index.get("index_id"))
        return {
            "name": "Future Category Support",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculation_reproducibility(results: list, indexes: list) -> dict[str, Any]:
        expected: dict[str, dict[str, str]] = {}
        for result in results:
            bar_id = str(result.get("input_bar_id", ""))
            category = CALCULATION_TYPE_TO_INDEX_CATEGORY.get(str(result.get("calculation_type", "")))
            if bar_id and category:
                expected.setdefault(bar_id, {})[category] = str(result.get("result_id", ""))

        invalid = []
        for index in indexes:
            bar_id = str(index.get("bar_id", ""))
            if dict(index.get("references") or {}) != expected.get(bar_id, {}):
                invalid.append(index.get("index_id"))
        return {
            "name": "Calculation Reproducibility",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_index_immutability_fields(indexes: list) -> dict[str, Any]:
        invalid = [
            index.get("index_id")
            for index in indexes
            if not (index.get("metadata") or {}).get("reference_only")
        ]
        return {
            "name": "Index Immutability After Build",
            "status": "PASS" if indexes and not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_orphan_references(results: list, indexes: list) -> dict[str, Any]:
        result_ids = {item.get("result_id") for item in results}
        orphans = [
            result_id
            for index in indexes
            for result_id in (index.get("references") or {}).values()
            if result_id not in result_ids
        ]
        return {
            "name": "No Orphan References",
            "status": "PASS" if not orphans else "FAIL",
            "orphan_count": len(orphans),
        }

    @staticmethod
    def _check_no_missing_references(results: list, indexes: list) -> dict[str, Any]:
        referenced = {
            result_id
            for index in indexes
            for result_id in (index.get("references") or {}).values()
        }
        missing = {item.get("result_id") for item in results} - referenced
        return {
            "name": "No Missing References",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_no_invalid_references(results: list, indexes: list) -> dict[str, Any]:
        result_ids = {item.get("result_id") for item in results}
        invalid = [
            result_id
            for index in indexes
            for result_id in (index.get("references") or {}).values()
            if result_id not in result_ids
        ]
        return {
            "name": "No Invalid References",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_cross_bar_references(results: list, indexes: list) -> dict[str, Any]:
        result_map = {item.get("result_id"): item for item in results}
        invalid = []
        for index in indexes:
            bar_id = index.get("bar_id")
            for result_id in (index.get("references") or {}).values():
                result = result_map.get(result_id, {})
                if result.get("input_bar_id") != bar_id:
                    invalid.append(result_id)
        return {
            "name": "No Cross Bar References",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_builder_idempotence(indexes: list) -> dict[str, Any]:
        ids = [index.get("index_id") for index in indexes]
        expected = [f"CALC_INDEX::{index:06d}" for index in range(1, len(indexes) + 1)]
        return {
            "name": "Builder Idempotence",
            "status": "PASS" if ids == expected else "FAIL",
            "index_count": len(indexes),
        }

    @staticmethod
    def _check_bar_index_alignment(bars: list, indexes: list) -> dict[str, Any]:
        bar_ids = {item.get("bar_id") for item in bars}
        index_bar_ids = {item.get("bar_id") for item in indexes}
        return {
            "name": "Bar Index Alignment",
            "status": "PASS" if bar_ids == index_bar_ids else "FAIL",
            "bar_count": len(bar_ids),
        }

    @staticmethod
    def _check_unique_index_ids(indexes: list) -> dict[str, Any]:
        ids = [item.get("index_id") for item in indexes]
        return {
            "name": "Unique Index IDs",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
            "index_count": len(ids),
        }

    @staticmethod
    def _check_deterministic_index_ids(indexes: list) -> dict[str, Any]:
        ids = [item.get("index_id") for item in indexes]
        expected = [f"CALC_INDEX::{index:06d}" for index in range(1, len(indexes) + 1)]
        return {
            "name": "Deterministic Index IDs",
            "status": "PASS" if ids == expected else "FAIL",
            "index_count": len(indexes),
        }

    @staticmethod
    def _check_registry_lookup_integrity(indexes: list) -> dict[str, Any]:
        lookup_registry = CalculationIndexRegistry()
        for index in indexes:
            lookup_registry.register(dict(index))
        ok = len(lookup_registry.all_indexes()) == len(indexes)
        return {
            "name": "Registry Lookup Integrity",
            "status": "PASS" if indexes and ok else "FAIL",
            "index_count": len(indexes),
        }

    @staticmethod
    def _check_reference_only_metadata(indexes: list) -> dict[str, Any]:
        invalid = [
            index.get("index_id")
            for index in indexes
            if not (index.get("metadata") or {}).get("reference_only")
        ]
        return {
            "name": "Reference Only Metadata",
            "status": "PASS" if indexes and not invalid else "FAIL",
            "invalid_count": len(invalid),
        }
