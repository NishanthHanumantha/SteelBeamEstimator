"""
Recovery Reporter — builds the three report payloads for Phase L.2.2.

Reports produced
----------------
geometry_recovery_report.json     Per-beam recovery status + statistics.
beam_coverage_matrix.json          Full coverage matrix across all pipeline stages.
pipeline_validation_report.json   Consistency rule results + pipeline status.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

PHASE = "L.2.2"
MODEL_VERSION = "6.4.2"


def build_geometry_recovery_report(
    all_beam_ids: List[str],
    gap_beam_ids: List[str],
    recovery_results: List[Dict[str, Any]],
    geometry_registry_dict: Dict[str, Any],
    run_timestamp: str,
    duration_s: float,
) -> Dict[str, Any]:
    """Build geometry_recovery_report payload."""
    recovered = [r for r in recovery_results if r.get("status") == "RECOVERED"]
    failed = [r for r in recovery_results if r.get("status") == "FAILED"]
    total_beams = len(all_beam_ids)
    recovered_count = len(recovered)
    failed_count = len(failed)
    recovery_rate = round(100 * recovered_count / max(len(gap_beam_ids), 1), 2) if gap_beam_ids else 100.0

    per_beam: List[Dict[str, Any]] = []
    for bid in all_beam_ids:
        if bid not in gap_beam_ids:
            per_beam.append({
                "beam_id": bid,
                "status": "ORIGINAL",
                "geometry_source": "ORIGINAL",
                "in_gap": False,
            })
        else:
            result = next((r for r in recovery_results if r["beam_id"] == bid), None)
            per_beam.append({
                "beam_id": bid,
                "status": result.get("status", "UNKNOWN") if result else "UNKNOWN",
                "geometry_source": "RECOVERED" if (result and result.get("status") == "RECOVERED") else "FAILED",
                "geometry_id": (result or {}).get("geometry_id"),
                "confidence": (result or {}).get("confidence"),
                "recovery_sources": (result or {}).get("recovery_sources", []),
                "placeholder_bars": (result or {}).get("placeholder_bars", 0),
                "in_gap": True,
            })

    return {
        "phase": PHASE,
        "model_version": MODEL_VERSION,
        "report_type": "geometry_recovery_report",
        "run_timestamp": run_timestamp,
        "duration_s": round(duration_s, 3),
        "summary": {
            "total_detected_beams": total_beams,
            "beams_with_original_geometry": total_beams - len(gap_beam_ids),
            "gap_beams_identified": len(gap_beam_ids),
            "recovered_count": recovered_count,
            "failed_count": failed_count,
            "recovery_rate_percent": recovery_rate,
        },
        "per_beam_status": per_beam,
        "geometry_registry_summary": {
            "total": geometry_registry_dict.get("total"),
            "original_count": geometry_registry_dict.get("original_count"),
            "recovered_count": geometry_registry_dict.get("recovered_count"),
            "failed_count": geometry_registry_dict.get("failed_count"),
        },
    }


def build_beam_coverage_matrix_report(
    coverage_result: Dict[str, Any],
    run_timestamp: str,
) -> Dict[str, Any]:
    """Build beam_coverage_matrix payload."""
    return {
        "phase": PHASE,
        "model_version": MODEL_VERSION,
        "report_type": "beam_coverage_matrix",
        "run_timestamp": run_timestamp,
        "summary": {
            "total_beams": coverage_result.get("total_beams"),
            "beams_pass": coverage_result.get("beams_pass"),
            "beams_fail": coverage_result.get("beams_fail"),
            "coverage_percent": coverage_result.get("coverage_percent"),
        },
        "source_counts": coverage_result.get("source_counts"),
        "coverage_matrix": coverage_result.get("coverage_matrix"),
    }


def build_pipeline_validation_report(
    consistency_result: Dict[str, Any],
    coverage_result: Dict[str, Any],
    traceability_summary: Dict[str, Any],
    run_timestamp: str,
) -> Dict[str, Any]:
    """Build pipeline_validation_report payload."""
    counts = consistency_result.get("counts") or {}
    return {
        "phase": PHASE,
        "model_version": MODEL_VERSION,
        "report_type": "pipeline_validation_report",
        "run_timestamp": run_timestamp,
        "pipeline_status": consistency_result.get("pipeline_status", "UNKNOWN"),
        "counts": counts,
        "coverage_percent": coverage_result.get("coverage_percent"),
        "consistency_rules": consistency_result.get("rules"),
        "failed_rules": consistency_result.get("failed_rules"),
        "traceability_summary": traceability_summary,
        "validation_details": {
            "detected_beams": counts.get("detected_beams"),
            "engineering_objects": counts.get("engineering_objects"),
            "specifications": counts.get("specifications"),
            "geometry_objects": counts.get("geometry_objects"),
            "feature_beams": counts.get("feature_beams"),
            "coverage_percent": coverage_result.get("coverage_percent"),
            "recovered_count": (
                traceability_summary.get("recovered_geometry_beams")
            ),
            "failed_count": (
                traceability_summary.get("beams_validation_fail")
            ),
        },
    }
