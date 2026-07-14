"""
Geometry Traceability Registry.

Every Engineering Feature must be traceable to a specific geometry object.
This module:
  1. Builds a traceability map: bar_id → geometry traceability record.
  2. Generates the traceability extension for every feature.

Each traceability record carries:
  geometry_id           Canonical geometry identifier.
  geometry_source       ORIGINAL | RECOVERED.
  creation_stage        L2_ORIGINAL | L2_2_GEOMETRY_RECOVERY.
  beam_validation_status PASS | WARNING | FAIL.
  feature_generation_time ISO-8601 timestamp (from parent run).
  confidence            Geometry confidence score.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def build_traceability_map(
    geometry_registry_dict: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Build a beam_id → traceability record mapping from the geometry registry.

    Returns
    -------
    Dict[beam_id, traceability_record]
    """
    traceability: Dict[str, Dict[str, Any]] = {}
    for entry in geometry_registry_dict.get("entries") or []:
        beam_id = entry.get("beam_id", "UNKNOWN")
        status = entry.get("status", "FAILED")
        source = entry.get("source", "UNKNOWN")
        beam_val_status = (
            "PASS" if status in ("PRESENT", "RECOVERED")
            else "FAIL"
        )
        traceability[beam_id] = {
            "geometry_id": entry.get("geometry_id", ""),
            "geometry_source": source,
            "creation_stage": entry.get("creation_stage", ""),
            "beam_validation_status": beam_val_status,
            "confidence": entry.get("confidence", 0.0),
        }
    return traceability


def enrich_feature_traceability(
    feature_traceability: Dict[str, Any],
    beam_id: str,
    traceability_map: Dict[str, Dict[str, Any]],
    run_timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Enrich an existing feature traceability dict with geometry source fields.

    Parameters
    ----------
    feature_traceability:
        The existing ``traceability`` dict on an EngineeringFeatureModel.
    beam_id:
        The beam this feature belongs to.
    traceability_map:
        Produced by :func:`build_traceability_map`.
    run_timestamp:
        ISO-8601 string for feature_generation_time.

    Returns
    -------
    Enriched traceability dict (original fields preserved, geometry fields added).
    """
    record = traceability_map.get(beam_id) or {}
    ts = run_timestamp or datetime.now(timezone.utc).isoformat()
    enriched = dict(feature_traceability)
    enriched.update(
        {
            "geometry_id": record.get("geometry_id", ""),
            "geometry_source": record.get("geometry_source", "UNKNOWN"),
            "creation_stage": record.get("creation_stage", ""),
            "feature_generation_time": ts,
            "beam_validation_status": record.get("beam_validation_status", "UNKNOWN"),
            "geometry_confidence": record.get("confidence", 0.0),
        }
    )
    return enriched


def build_traceability_summary(
    traceability_map: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Return aggregate statistics over the traceability map."""
    total = len(traceability_map)
    original = sum(
        1 for r in traceability_map.values() if r.get("geometry_source") == "ORIGINAL"
    )
    recovered = sum(
        1 for r in traceability_map.values() if r.get("geometry_source") == "RECOVERED"
    )
    pass_count = sum(
        1 for r in traceability_map.values() if r.get("beam_validation_status") == "PASS"
    )
    return {
        "total_beams_traced": total,
        "original_geometry_beams": original,
        "recovered_geometry_beams": recovered,
        "beams_validation_pass": pass_count,
        "beams_validation_fail": total - pass_count,
        "coverage_percent": round(100 * pass_count / max(total, 1), 2),
    }
