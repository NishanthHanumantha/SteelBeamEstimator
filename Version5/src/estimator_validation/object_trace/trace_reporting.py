"""Engineering trace reporting — Phase QA.2."""

from __future__ import annotations

from typing import Any, List


class TraceReporting:
    @staticmethod
    def build(trace_result: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
        traces = trace_result.get("engineering_traces", [])
        failures = [
            item for item in traces if item.get("trace_status") != "PASS"
        ]
        failures.sort(
            key=lambda item: (
                0 if item.get("first_missing_layer") in {"drawing", "identity"} else 1,
                item.get("identity", {}).get("beam_mark", ""),
                item.get("identity", {}).get("role", ""),
            )
        )
        top_failures = failures[:25]
        per_beam = TraceReporting._group_by(traces, "beam_mark")
        per_role = TraceReporting._group_by(traces, "role")
        per_diameter = TraceReporting._group_by(traces, "diameter_mm")
        per_layer = summary.get("first_missing_layer_distribution", {})
        return {
            "phase": "Phase QA.2",
            "overall_trace_summary": summary,
            "per_beam_trace": per_beam,
            "per_role_trace": per_role,
            "per_diameter_trace": per_diameter,
            "per_layer_trace": per_layer,
            "geometry_comparison_summary": {
                "beam_count": trace_result.get("geometry_comparison", {}).get("beam_count", 0),
                "sample_conclusions": [
                    item.get("conclusion")
                    for item in trace_result.get("geometry_comparison", {}).get("beams", [])[:5]
                ],
            },
            "identity_match_quality": trace_result.get("identity_matching", {}),
            "false_positional_match_report": {
                "false_positional_mismatches": trace_result.get("identity_matching", {}).get(
                    "false_positional_mismatches", 0
                ),
                "qa1_conclusion": trace_result.get("qa1_validation", {}).get("conclusion"),
            },
            "first_missing_layer_distribution": per_layer,
            "root_cause_matrix": trace_result.get("root_cause_matrix", {}),
            "top_25_engineering_trace_failures": top_failures,
            "recommended_fix_order": TraceReporting._recommended_fix_order(trace_result),
        }

    @staticmethod
    def _group_by(traces: List[dict[str, Any]], field: str) -> dict[str, dict[str, int]]:
        grouped: dict[str, dict[str, int]] = {}
        for trace in traces:
            identity = trace.get("identity", {})
            key = str(identity.get(field) if field != "beam_mark" and field != "role" else identity.get(field, "UNKNOWN"))
            if field == "beam_mark":
                key = str(identity.get("beam_mark", "UNKNOWN"))
            elif field == "role":
                key = str(identity.get("role", "UNKNOWN"))
            grouped.setdefault(key, {"PASS": 0, "FAIL": 0})
            grouped[key][trace.get("trace_status", "FAIL")] += 1
        return grouped

    @staticmethod
    def _recommended_fix_order(trace_result: dict[str, Any]) -> List[dict[str, Any]]:
        distribution = trace_result.get("trace_statistics", {}).get("first_missing_layer_distribution", {})
        order = []
        phase_map = {
            "drawing": ("Drawing Parser / I.2", "HIGH"),
            "identity": ("Bar Identity I.8", "MEDIUM"),
            "bar_group": ("Bar Group I.9", "MEDIUM"),
            "bbs": ("BBS I.10", "MEDIUM"),
            "steel_weight": ("Steel Weight I.11", "MEDIUM"),
            "beam_summary": ("Beam Summary I.12", "MEDIUM"),
            "quantity": ("Quantity I.13", "MEDIUM"),
            "material": ("Material I.14", "LOW"),
            "beam_schedule": ("Beam Schedule I.15", "HIGH"),
            "engineering_report": ("Engineering Report I.16", "HIGH"),
            "excel": ("Excel Export I.17", "LOW"),
        }
        for layer, count in sorted(distribution.items(), key=lambda item: item[1], reverse=True):
            if layer == "NONE":
                continue
            phase, risk = phase_map.get(layer, ("Unknown", "MEDIUM"))
            order.append({"layer": layer, "count": count, "recommended_phase": phase, "estimated_risk": risk})
        return order
