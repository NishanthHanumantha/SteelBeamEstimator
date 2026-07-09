"""Quantity state definitions, stage ordering, and downstream trace builder."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Tuple

class QuantityState(str, Enum):
    UNKNOWN = "UNKNOWN"
    OBJECT_CREATED = "OBJECT_CREATED"
    NORMALIZED = "NORMALIZED"
    CALCULATED = "CALCULATED"
    STEEL_READY = "STEEL_READY"
    STEEL_GENERATED = "STEEL_GENERATED"
    BBS_READY = "BBS_READY"
    BBS_WRITTEN = "BBS_WRITTEN"
    EXCEL_READY = "EXCEL_READY"
    EXCEL_WRITTEN = "EXCEL_WRITTEN"
    QA_VISIBLE = "QA_VISIBLE"
    BLOCKED = "BLOCKED"
    DEFERRED = "DEFERRED"
    FAILED = "FAILED"


QUANTITY_STATES: Tuple[str, ...] = tuple(state.value for state in QuantityState)

STAGE_ORDER: Tuple[Tuple[str, str], ...] = (
    ("engineering_object", "Engineering Object"),
    ("normalization", "Normalization"),
    ("calculation", "Calculation"),
    ("steel_weight", "Steel Weight"),
    ("engineering_report", "Engineering Report"),
    ("beam_schedule", "Beam Schedule"),
    ("excel_export", "Excel Export"),
    ("qa_aggregation", "QA Aggregation"),
)

QUANTITY_CALC_TYPES: Tuple[str, ...] = (
    "BAR_IDENTITY",
    "SHAPE_CODE",
    "CUT_LENGTH",
    "LAP_LENGTH",
    "STEEL_WEIGHT",
)

DEPENDENCY_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("geometry", "geometry"),
    ("specification", "specification_id"),
    ("length", "length"),
    ("development_length", "development_length"),
    ("cut_length", "cut_length"),
    ("diameter", "diameter_mm"),
    ("quantity", "quantity"),
    ("steel_density", "density"),
    ("lifecycle_state", "lifecycle_state"),
    ("availability", "availability"),
    ("calculation_result", "calculation_result"),
    ("weight_result", "weight_result"),
    ("engineering_report_entry", "engineering_report_entry"),
    ("bbs_entry", "bbs_entry"),
    ("excel_entry", "excel_entry"),
)


def build_stage_trace(stages: Dict[str, dict[str, Any]]) -> List[dict[str, Any]]:
    trace: List[dict[str, Any]] = []
    prior_failed = False
    for stage_key, label in STAGE_ORDER:
        stage = stages.get(stage_key) or {}
        passed = stage.get("status") == "PASS"
        if prior_failed and not passed:
            status = "INHERITED_FAIL"
        else:
            status = "PASS" if passed else "FAIL"
        trace.append(
            {
                "stage": stage_key,
                "label": label,
                "status": status,
                "reason": stage.get("reason"),
            }
        )
        if not passed:
            prior_failed = True
    return trace


class QuantityTraceabilityBuilder:
    """Construct per-recovery downstream trace records."""

    def build_all(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        from src.engineering_quantity_validation.integration_stage_analyzer import IntegrationStageAnalyzer

        stage_analysis = IntegrationStageAnalyzer().analyze_all(snapshot)
        traces: List[dict[str, Any]] = []

        for entry, analysis in zip(snapshot.get("registry_entries") or [], stage_analysis.get("analyses") or []):
            stages = analysis.get("stages") or {}
            traces.append(
                {
                    "recovery_id": entry.get("recovery_id"),
                    "discovery_id": entry.get("discovery_id"),
                    "bar_id": entry.get("normalized_bar_id"),
                    "beam_id": entry.get("beam_id"),
                    "stage_trace": build_stage_trace(stages),
                    "stages": {
                        key: {"status": value.get("status"), "reason": value.get("reason")}
                        for key, value in stages.items()
                    },
                    "first_failure_stage": analysis.get("first_failure_stage"),
                    "first_failure_label": analysis.get("first_failure_label"),
                    "primary_blocking_reason": analysis.get("primary_blocking_reason"),
                    "current_quantity_state": analysis.get("current_quantity_state"),
                }
            )

        return {
            "trace_count": len(traces),
            "traces": traces,
            "first_failure_distribution": stage_analysis.get("first_failure_distribution"),
            "stage_analyses": stage_analysis.get("analyses") or [],
        }
