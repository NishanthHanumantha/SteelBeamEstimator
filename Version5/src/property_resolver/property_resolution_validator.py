"""Validate resolved Engineering Properties — Phase G.5.3.2 / lifecycle G.5.3.4."""

from __future__ import annotations

import math
import statistics
from typing import Any, List, Set

from src.property_resolver.property_availability import (
    CURRENT_PIPELINE_PHASE,
    PROPERTY_STATUS_NOT_AVAILABLE_YET,
    PROPERTY_STATUS_UNKNOWN,
    VALID_PROPERTY_STATUSES,
    build_property_availability_report,
    get_property_available_phase,
    get_property_lifecycle,
    is_property_available,
)
from src.property_resolver.property_lifecycle import (
    LIFECYCLE_AVAILABLE_FROM,
    PROPERTY_TYPE_LIFECYCLE,
    VALID_LIFECYCLES,
    EngineeringPropertyLifecycle,
)
from src.property_resolver.property_resolution_engine import PropertyResolutionEngine
from src.property_resolver.property_resolver import property_resolver_applied
from src.property_resolver.property_resolver_types import (
    RESOLUTION_CONFLICT,
    RESOLUTION_IDENTICAL,
    RESOLUTION_MAJORITY,
    RESOLUTION_UNKNOWN,
    VALID_RESOLUTION_STRATEGIES,
)


class PropertyResolutionValidator:
    """Verify property resolution integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not property_resolver_applied(model) and not model.get(
            "resolved_engineering_properties"
        ):
            return {
                "phase": "Phase G.5.3.4",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "property resolver not applied"},
            }

        properties = model.get("engineering_properties", [])
        resolved = model.get("resolved_engineering_properties", [])
        if not resolved:
            resolved = model.get("property_resolution_registry", {}).get(
                "resolved_properties", []
            )

        registry = model.get("property_resolution_registry", {})
        candidates = model.get("property_candidates", [])
        objects = model.get("engineering_objects", [])
        conflicts = model.get("property_conflicts", [])

        checks: List[dict[str, Any]] = []
        checks.append(self._check_property_coverage(properties, resolved))
        checks.append(self._check_resolution_coverage(properties, resolved, objects))
        checks.append(self._check_one_per_type(resolved))
        checks.append(self._check_selected_property_exists(properties, resolved))
        checks.append(self._check_selected_candidate_exists(candidates, resolved))
        checks.append(self._check_traceability(resolved, properties, candidates))
        checks.append(self._check_strategy_assigned(resolved))
        checks.append(self._check_confidence_assigned(resolved))
        checks.append(self._check_unique_resolved_ids(resolved))
        checks.append(self._check_registry_integrity(registry, properties, resolved, objects))
        checks.append(self._check_conflict_handling(resolved, conflicts))
        checks.append(self._check_exports_generated(model))
        checks.append(self._check_summary_consistency(model))
        checks.append(self._check_confidence_range(resolved))
        checks.append(self._check_unknown_zero_confidence(resolved))
        checks.append(self._check_identical_vs_majority_confidence(resolved))
        checks.append(self._check_conflict_vs_identical_confidence(resolved))
        checks.append(self._check_no_nan_confidence(resolved))
        checks.append(self._check_deterministic_confidence(properties))
        checks.append(self._check_summary_confidence_statistics(model, resolved))
        checks.append(self._check_property_type_lifecycle_mapping(resolved))
        checks.append(self._check_lifecycle_available_phase_mapping())
        checks.append(self._check_no_invalid_lifecycle(resolved))
        checks.append(self._check_deferred_not_unknown_status(resolved))
        checks.append(self._check_deferred_zero_confidence(resolved))
        checks.append(self._check_deferred_null_value(resolved))
        checks.append(self._check_lifecycle_metadata_complete(resolved))
        checks.append(self._check_summary_lifecycle_counts(model, resolved))
        checks.append(self._check_availability_report_consistency(model, resolved))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.5.3.4",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "engineering_property_count": len(properties),
                "resolved_property_count": len(resolved),
                "conflict_count": len(conflicts),
            },
        }

    @staticmethod
    def _check_property_coverage(
        properties: list,
        resolved: list,
    ) -> dict[str, Any]:
        property_ids = {p.get("property_id") for p in properties}
        referenced: Set[str] = set()
        for item in resolved:
            if item.get("selected_property_id"):
                referenced.add(item.get("selected_property_id"))
            referenced.update(item.get("alternative_property_ids", []))
        missing = sorted(property_ids - referenced)
        return {
            "name": "Property Coverage",
            "status": "PASS" if properties and not missing else "FAIL",
            "missing": missing[:10],
            "considered": len(property_ids) - len(missing),
            "total": len(property_ids),
        }

    @staticmethod
    def _check_resolution_coverage(
        properties: list,
        resolved: list,
        objects: list,
    ) -> dict[str, Any]:
        expected_keys = {
            (p.get("engineering_object_id"), p.get("property_type")) for p in properties
        }
        actual_keys = {
            (r.get("engineering_object_id"), r.get("property_type")) for r in resolved
        }
        missing = sorted(expected_keys - actual_keys)
        object_ids_with_props = {p.get("engineering_object_id") for p in properties}
        object_ids_resolved = {r.get("engineering_object_id") for r in resolved}
        unprocessed_objects = sorted(object_ids_with_props - object_ids_resolved)
        return {
            "name": "Resolution Coverage",
            "status": "PASS" if not missing and not unprocessed_objects else "FAIL",
            "missing_groups": [f"{obj}:{ptype}" for obj, ptype in missing[:10]],
            "unprocessed_objects": unprocessed_objects[:10],
            "expected_groups": len(expected_keys),
            "actual_groups": len(actual_keys),
            "engineering_object_count": len(objects),
        }

    @staticmethod
    def _check_one_per_type(resolved: list) -> dict[str, Any]:
        keys = [(r.get("engineering_object_id"), r.get("property_type")) for r in resolved]
        duplicates = len(keys) - len(set(keys))
        return {
            "name": "One Resolved Property Per Type",
            "status": "PASS" if duplicates == 0 else "FAIL",
            "duplicate_count": duplicates,
        }

    @staticmethod
    def _check_selected_property_exists(
        properties: list,
        resolved: list,
    ) -> dict[str, Any]:
        property_ids = {p.get("property_id") for p in properties}
        invalid = [
            r.get("resolved_property_id")
            for r in resolved
            if r.get("selected_property_id")
            and r.get("selected_property_id") not in property_ids
        ]
        return {
            "name": "Selected Property Exists",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_selected_candidate_exists(
        candidates: list,
        resolved: list,
    ) -> dict[str, Any]:
        candidate_ids = {c.get("candidate_id") for c in candidates}
        invalid = [
            r.get("resolved_property_id")
            for r in resolved
            if r.get("selected_candidate_id")
            and r.get("selected_candidate_id") not in candidate_ids
        ]
        return {
            "name": "Selected Candidate Exists",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_traceability(
        resolved: list,
        properties: list,
        candidates: list,
    ) -> dict[str, Any]:
        prop_map = {p.get("property_id"): p for p in properties}
        candidate_map = {c.get("candidate_id"): c for c in candidates}
        invalid = []
        for item in resolved:
            pid = item.get("selected_property_id")
            if not pid:
                continue
            prop = prop_map.get(pid, {})
            cand = candidate_map.get(item.get("selected_candidate_id"), {})
            if item.get("selected_source_entity") != prop.get("source_entity_id"):
                invalid.append(item.get("resolved_property_id"))
            if prop.get("candidate_id") != item.get("selected_candidate_id"):
                invalid.append(item.get("resolved_property_id"))
            if cand and prop.get("engineering_object_id") != item.get("engineering_object_id"):
                invalid.append(item.get("resolved_property_id"))
        return {
            "name": "Traceability Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_strategy_assigned(resolved: list) -> dict[str, Any]:
        invalid = [
            r.get("resolved_property_id")
            for r in resolved
            if r.get("resolution_strategy") not in VALID_RESOLUTION_STRATEGIES
        ]
        return {
            "name": "Resolution Strategies Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_confidence_assigned(resolved: list) -> dict[str, Any]:
        invalid = [
            r.get("resolved_property_id")
            for r in resolved
            if r.get("resolution_confidence") is None
        ]
        return {
            "name": "Resolution Confidence Assigned",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_unique_resolved_ids(resolved: list) -> dict[str, Any]:
        ids = [r.get("resolved_property_id") for r in resolved]
        return {
            "name": "IDs Unique",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
            "count": len(ids),
        }

    @staticmethod
    def _check_registry_integrity(
        registry: dict[str, Any],
        properties: list,
        resolved: list,
        objects: list,
    ) -> dict[str, Any]:
        ok = (
            registry.get("resolved_property_count") == len(resolved)
            and registry.get("engineering_property_count") == len(properties)
            and registry.get("engineering_object_count") == len(objects)
        )
        return {
            "name": "Registry Integrity",
            "status": "PASS" if resolved and ok else "FAIL",
            "registry_resolved_count": registry.get("resolved_property_count"),
            "actual_resolved_count": len(resolved),
        }

    @staticmethod
    def _check_conflict_handling(
        resolved: list,
        conflicts: list,
    ) -> dict[str, Any]:
        conflict_groups = {
            (c.get("engineering_object_id"), c.get("property_type")) for c in conflicts
        }
        invalid = []
        for item in resolved:
            key = (item.get("engineering_object_id"), item.get("property_type"))
            if key in conflict_groups and not item.get("conflicting_values"):
                invalid.append(item.get("resolved_property_id"))
        return {
            "name": "Conflict Handling Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
            "conflict_records": len(conflicts),
        }

    @staticmethod
    def _check_exports_generated(model: dict[str, Any]) -> dict[str, Any]:
        ok = bool(
            model.get("resolved_engineering_properties") is not None
            and model.get("property_resolution_registry")
            and model.get("property_conflicts") is not None
            and model.get("property_resolution_summary")
            and model.get("property_availability_report")
        )
        return {
            "name": "Export Generated",
            "status": "PASS" if ok else "FAIL",
        }

    @staticmethod
    def _check_summary_consistency(model: dict[str, Any]) -> dict[str, Any]:
        summary = model.get("property_resolution_summary", {})
        resolved = model.get("resolved_engineering_properties", [])
        properties = model.get("engineering_properties", [])
        ok = (
            summary.get("resolved_property_count") == len(resolved)
            and summary.get("engineering_property_count") == len(properties)
        )
        return {
            "name": "Summary Consistency",
            "status": "PASS" if summary and ok else "FAIL",
            "summary_resolved_count": summary.get("resolved_property_count"),
            "actual_resolved_count": len(resolved),
        }

    @staticmethod
    def _check_confidence_range(resolved: list) -> dict[str, Any]:
        invalid = [
            item.get("resolved_property_id")
            for item in resolved
            if not (0.0 <= float(item.get("resolution_confidence", -1.0)) <= 1.0)
        ]
        return {
            "name": "Confidence Range Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_unknown_zero_confidence(resolved: list) -> dict[str, Any]:
        invalid = [
            item.get("resolved_property_id")
            for item in resolved
            if item.get("resolution_strategy") == RESOLUTION_UNKNOWN
            and float(item.get("resolution_confidence", -1.0)) != 0.0
        ]
        return {
            "name": "UNKNOWN Confidence Zero",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_identical_vs_majority_confidence(resolved: list) -> dict[str, Any]:
        identical = [
            float(item.get("resolution_confidence", 0.0))
            for item in resolved
            if item.get("resolution_strategy") == RESOLUTION_IDENTICAL
        ]
        majority = [
            float(item.get("resolution_confidence", 0.0))
            for item in resolved
            if item.get("resolution_strategy") == RESOLUTION_MAJORITY
        ]
        if not identical or not majority:
            return {
                "name": "IDENTICAL Confidence >= MAJORITY Average",
                "status": "PASS",
                "reason": "insufficient strategy samples",
            }
        identical_avg = sum(identical) / len(identical)
        majority_avg = sum(majority) / len(majority)
        return {
            "name": "IDENTICAL Confidence >= MAJORITY Average",
            "status": "PASS" if identical_avg >= majority_avg else "FAIL",
            "identical_average": round(identical_avg, 4),
            "majority_average": round(majority_avg, 4),
        }

    @staticmethod
    def _check_conflict_vs_identical_confidence(resolved: list) -> dict[str, Any]:
        identical = [
            float(item.get("resolution_confidence", 0.0))
            for item in resolved
            if item.get("resolution_strategy") == RESOLUTION_IDENTICAL
        ]
        conflict = [
            float(item.get("resolution_confidence", 0.0))
            for item in resolved
            if item.get("resolution_strategy") == RESOLUTION_CONFLICT
        ]
        if not identical or not conflict:
            return {
                "name": "CONFLICT Confidence < IDENTICAL Average",
                "status": "PASS",
                "reason": "insufficient strategy samples",
            }
        identical_avg = sum(identical) / len(identical)
        conflict_avg = sum(conflict) / len(conflict)
        return {
            "name": "CONFLICT Confidence < IDENTICAL Average",
            "status": "PASS" if conflict_avg < identical_avg else "FAIL",
            "conflict_average": round(conflict_avg, 4),
            "identical_average": round(identical_avg, 4),
        }

    @staticmethod
    def _check_no_nan_confidence(resolved: list) -> dict[str, Any]:
        invalid = [
            item.get("resolved_property_id")
            for item in resolved
            if math.isnan(float(item.get("resolution_confidence", 0.0)))
            or math.isinf(float(item.get("resolution_confidence", 0.0)))
        ]
        return {
            "name": "No NaN Confidence",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_deterministic_confidence(properties: list) -> dict[str, Any]:
        if not properties:
            return {
                "name": "Deterministic Confidence",
                "status": "PASS",
                "reason": "no properties",
            }
        engine = PropertyResolutionEngine()
        first, _, _ = engine.resolve(properties)
        second, _, _ = engine.resolve(properties)
        first_map = {
            (item.get("engineering_object_id"), item.get("property_type")): float(
                item.get("resolution_confidence", 0.0)
            )
            for item in first
        }
        mismatches = []
        for item in second:
            key = (item.get("engineering_object_id"), item.get("property_type"))
            if first_map.get(key) != float(item.get("resolution_confidence", 0.0)):
                mismatches.append(key)
        return {
            "name": "Deterministic Confidence",
            "status": "PASS" if not mismatches else "FAIL",
            "mismatch_count": len(mismatches),
        }

    @staticmethod
    def _check_summary_confidence_statistics(
        model: dict[str, Any],
        resolved: list,
    ) -> dict[str, Any]:
        summary = model.get("property_resolution_summary", {})
        confidences = [float(item.get("resolution_confidence", 0.0)) for item in resolved]
        if not summary or not confidences:
            return {
                "name": "Summary Confidence Statistics Consistent",
                "status": "PASS" if not confidences else "FAIL",
            }
        expected_avg = round(sum(confidences) / len(confidences), 4)
        expected_min = round(min(confidences), 4)
        expected_max = round(max(confidences), 4)
        expected_median = round(statistics.median(confidences), 4)
        ok = (
            summary.get("average_resolution_confidence") == expected_avg
            and summary.get("minimum_resolution_confidence") == expected_min
            and summary.get("maximum_resolution_confidence") == expected_max
            and summary.get("median_resolution_confidence") == expected_median
        )
        return {
            "name": "Summary Confidence Statistics Consistent",
            "status": "PASS" if ok else "FAIL",
            "expected_average": expected_avg,
            "summary_average": summary.get("average_resolution_confidence"),
        }

    @staticmethod
    def _check_property_type_lifecycle_mapping(resolved: list) -> dict[str, Any]:
        missing = sorted(
            {
                str(item.get("property_type", ""))
                for item in resolved
                if str(item.get("property_type", "")).upper() not in PROPERTY_TYPE_LIFECYCLE
                and str(item.get("property_type", "")) != "UNKNOWN"
            }
        )
        return {
            "name": "Property Type Lifecycle Mapping",
            "status": "PASS" if not missing else "FAIL",
            "missing": missing[:10],
        }

    @staticmethod
    def _check_lifecycle_available_phase_mapping() -> dict[str, Any]:
        missing = [
            lifecycle.value
            for lifecycle in EngineeringPropertyLifecycle
            if lifecycle not in LIFECYCLE_AVAILABLE_FROM
        ]
        return {
            "name": "Lifecycle Available Phase Mapping",
            "status": "PASS" if not missing else "FAIL",
            "missing": missing,
        }

    @staticmethod
    def _check_no_invalid_lifecycle(resolved: list) -> dict[str, Any]:
        invalid = [
            item.get("resolved_property_id")
            for item in resolved
            if item.get("lifecycle") not in VALID_LIFECYCLES
        ]
        return {
            "name": "No Invalid Lifecycle",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_deferred_not_unknown_status(resolved: list) -> dict[str, Any]:
        invalid = [
            item.get("resolved_property_id")
            for item in resolved
            if not is_property_available(str(item.get("property_type", "")), CURRENT_PIPELINE_PHASE)
            and item.get("property_status") == PROPERTY_STATUS_UNKNOWN
        ]
        return {
            "name": "Deferred Properties Not UNKNOWN Status",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_deferred_zero_confidence(resolved: list) -> dict[str, Any]:
        invalid = [
            item.get("resolved_property_id")
            for item in resolved
            if item.get("property_status") == PROPERTY_STATUS_NOT_AVAILABLE_YET
            and float(item.get("resolution_confidence", -1.0)) != 0.0
        ]
        return {
            "name": "Deferred Properties Zero Confidence",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_deferred_null_value(resolved: list) -> dict[str, Any]:
        invalid = [
            item.get("resolved_property_id")
            for item in resolved
            if item.get("property_status") == PROPERTY_STATUS_NOT_AVAILABLE_YET
            and item.get("resolved_value") is not None
        ]
        return {
            "name": "Deferred Properties Null Value",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_lifecycle_metadata_complete(resolved: list) -> dict[str, Any]:
        invalid = [
            item.get("resolved_property_id")
            for item in resolved
            if not item.get("lifecycle")
            or not item.get("available_from_phase")
            or not item.get("property_status")
            or not item.get("availability_reason")
            or item.get("property_status") not in VALID_PROPERTY_STATUSES
        ]
        return {
            "name": "Lifecycle Metadata Complete",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_summary_lifecycle_counts(model: dict[str, Any], resolved: list) -> dict[str, Any]:
        summary = model.get("property_resolution_summary", {})
        expected_lifecycle: dict[str, int] = {}
        expected_status: dict[str, int] = {}
        for item in resolved:
            expected_lifecycle[str(item.get("lifecycle", ""))] = (
                expected_lifecycle.get(str(item.get("lifecycle", "")), 0) + 1
            )
            expected_status[str(item.get("property_status", ""))] = (
                expected_status.get(str(item.get("property_status", "")), 0) + 1
            )
        ok = (
            summary.get("lifecycle_distribution") == expected_lifecycle
            and summary.get("status_distribution") == expected_status
        )
        return {
            "name": "Summary Lifecycle Counts Consistent",
            "status": "PASS" if summary and ok else "FAIL",
        }

    @staticmethod
    def _check_availability_report_consistency(
        model: dict[str, Any],
        resolved: list,
    ) -> dict[str, Any]:
        report = model.get("property_availability_report", {})
        expected = build_property_availability_report(resolved, CURRENT_PIPELINE_PHASE)
        ok = (
            report.get("total_resolved_properties") == expected.get("total_resolved_properties")
            and report.get("deferred_count") == expected.get("deferred_count")
            and report.get("available_count") == expected.get("available_count")
            and len(report.get("property_types", [])) == len(expected.get("property_types", []))
        )
        return {
            "name": "Availability Report Consistent",
            "status": "PASS" if report and ok else "FAIL",
        }
