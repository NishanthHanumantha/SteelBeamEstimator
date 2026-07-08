"""Build engineering object creation traces and root cause chains."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class EngineeringObjectTraceBuilder:
    """Construct per-callout engineering object creation traces."""

    def build_trace(
        self,
        item: dict[str, Any],
        dependencies: dict[str, Any],
        readiness: dict[str, Any],
        decision: dict[str, Any],
    ) -> dict[str, Any]:
        pipeline = item.get("pipeline_trace") or {}
        created = decision.get("engineering_object_created", False)
        stages = [
            {"stage": "classification", "status": "SUCCESS" if item.get("classified") else "FAILED"},
            {
                "stage": "beam_association",
                "status": "SUCCESS" if item.get("associated") else "FAILED",
                "beam": item.get("beam_association"),
            },
            {
                "stage": "geometry_available",
                "status": "YES" if dependencies.get("geometry", {}).get("present") else "NO",
            },
            {
                "stage": "engineering_specification",
                "status": "YES" if dependencies.get("specification", {}).get("present") else "NO",
            },
            {
                "stage": "position",
                "status": readiness.get("components", {}).get("position", {}).get("present", False),
                "value": item.get("role"),
            },
            {
                "stage": "diameter",
                "status": item.get("diameter_mm") is not None,
                "value": item.get("diameter_mm"),
            },
            {
                "stage": "quantity",
                "status": item.get("quantity") is not None,
                "value": item.get("quantity"),
            },
            {
                "stage": "engineering_object",
                "status": "SUCCESS" if created else "FAILED",
                "engineering_object_id": item.get("engineering_object_id"),
                "normalized_bar_id": item.get("normalized_bar_id"),
            },
        ]
        if not created:
            stages.append(
                {
                    "stage": "rejection",
                    "status": "FAILED",
                    "primary_rejection_code": decision.get("primary_rejection_code"),
                    "secondary_codes": decision.get("secondary_codes", []),
                }
            )
        return {
            "discovery_id": item.get("discovery_id"),
            "original_text": item.get("original_text"),
            "beam_association": item.get("beam_association"),
            "stages": stages,
            "engineering_object_created": created,
            "primary_rejection_code": decision.get("primary_rejection_code"),
            "readiness_score": readiness.get("readiness_score"),
        }

    def build_root_cause_chain(
        self,
        item: dict[str, Any],
        decision: dict[str, Any],
        dependencies: dict[str, Any],
    ) -> dict[str, Any]:
        pipeline = item.get("pipeline_trace") or {}
        chain: List[dict[str, Any]] = [
            {"step": "detected", "status": "PASS" if pipeline.get("text_detected") else "FAIL"},
            {"step": "classified", "status": "PASS" if item.get("classified") else "FAIL"},
            {"step": "associated", "status": "PASS" if item.get("associated") else "FAIL"},
            {
                "step": "geometry_ready",
                "status": "PASS" if dependencies.get("geometry", {}).get("present") else "FAIL",
            },
            {
                "step": "specification_ready",
                "status": "PASS" if dependencies.get("specification", {}).get("present") else "FAIL",
            },
        ]
        if decision.get("engineering_object_created"):
            chain.extend(
                [
                    {"step": "engineering_object_created", "status": "PASS"},
                    {"step": "normalized", "status": "PASS" if pipeline.get("normalized") else "FAIL"},
                    {"step": "calculated", "status": "PASS" if pipeline.get("calculated") else "FAIL"},
                    {"step": "exported", "status": "PASS" if pipeline.get("written_to_excel") else "FAIL"},
                ]
            )
        else:
            blocking = self._blocking_step(dependencies, decision)
            chain.append({"step": blocking, "status": "FAIL"})
            chain.extend(
                [
                    {"step": "engineering_object_rejected", "status": "FAIL"},
                    {"step": "never_normalized", "status": "FAIL"},
                    {"step": "never_calculated", "status": "FAIL"},
                    {"step": "never_exported", "status": "FAIL"},
                ]
            )
        return {
            "discovery_id": item.get("discovery_id"),
            "original_text": item.get("original_text"),
            "primary_rejection_code": decision.get("primary_rejection_code"),
            "chain": chain,
        }

    @staticmethod
    def _blocking_step(dependencies: dict[str, Any], decision: dict[str, Any]) -> str:
        code = decision.get("primary_rejection_code")
        mapping = {
            "MISSING_GEOMETRY": "geometry_missing",
            "MISSING_SECTION": "section_missing",
            "MISSING_SPECIFICATION": "specification_missing",
            "MISSING_POSITION": "position_missing",
            "MISSING_BAR_ROLE": "role_missing",
            "DUPLICATE_SUPPRESSED": "duplicate_resolution",
        }
        if code in mapping:
            return mapping[code]
        first_missing = dependencies.get("first_missing_dependency")
        if first_missing:
            return f"{first_missing}_missing"
        return "engineering_object_blocked"

    def build_decision_matrix_record(
        self,
        item: dict[str, Any],
        dependencies: dict[str, Any],
        readiness: dict[str, Any],
        decision: dict[str, Any],
        recommendation: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "discovery_id": item.get("discovery_id"),
            "original_text": item.get("original_text"),
            "beam": item.get("beam_association"),
            "category": item.get("category"),
            "geometry_ready": dependencies.get("geometry", {}).get("present", False),
            "specification_ready": dependencies.get("specification", {}).get("present", False),
            "role_ready": dependencies.get("role", {}).get("present", False),
            "position_ready": dependencies.get("position", {}).get("present", False),
            "engineering_object_created": decision.get("engineering_object_created", False),
            "primary_rejection_code": decision.get("primary_rejection_code"),
            "secondary_codes": decision.get("secondary_codes", []),
            "readiness_score": readiness.get("readiness_score"),
            "recommendation": (recommendation or {}).get("recommendation"),
            "decision_timestamp": datetime.now(timezone.utc).isoformat(),
        }
