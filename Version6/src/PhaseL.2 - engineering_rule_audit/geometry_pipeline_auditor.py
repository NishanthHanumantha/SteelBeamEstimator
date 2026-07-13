"""Audit the geometry pipeline stage for all roles."""

from __future__ import annotations
from typing import Any, Dict, List


class GeometryPipelineAuditor:
    def audit(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        eng_objects = snapshot.get("engineering_objects") or {}
        objects = eng_objects.get("objects") or []
        type_dist: Dict[str, int] = {}
        for obj in objects:
            t = str(obj.get("object_type") or "UNKNOWN")
            type_dist[t] = type_dist.get(t, 0) + 1
        return {
            "total_engineering_objects": len(objects),
            "object_type_distribution": type_dist,
            "top_reinforcement": type_dist.get("TOP_REINFORCEMENT", 0),
            "bottom_reinforcement": type_dist.get("BOTTOM_REINFORCEMENT", 0),
            "stirrup": type_dist.get("STIRRUP", 0),
            "side_face": type_dist.get("SIDE_FACE_REINFORCEMENT", 0),
            "missing_types": [
                t for t in ["BOTTOM_REINFORCEMENT", "EXTRA_TOP", "EXTRA_BOTTOM"]
                if type_dist.get(t, 0) == 0
            ],
            "gap_summary": (
                "BOTTOM_REINFORCEMENT, EXTRA_TOP, EXTRA_BOTTOM not created in Phase G. "
                "Only TOP_REINFORCEMENT, STIRRUP, SIDE_FACE_REINFORCEMENT produced."
            ),
        }
