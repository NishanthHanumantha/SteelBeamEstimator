"""
Geometry Registry — builds and stores a canonical geometry entry per beam.

For every beam the registry records:
  • geometry_id
  • beam_id
  • source          (ORIGINAL | RECOVERED)
  • creation_stage  (L2_ORIGINAL | L2_2_GEOMETRY_RECOVERY)
  • confidence
  • bounding_box    {x_min, y_min, x_max, y_max, width_mm, depth_mm}
  • beam_axis       {start_x, start_y, end_x, end_y, length_mm}
  • start_node      {x, y}
  • end_node        {x, y}
  • support_locations
  • status          (PRESENT | RECOVERED | FAILED)
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional


_RECOVERY_STAGE = "L2_2_GEOMETRY_RECOVERY"
_ORIGINAL_STAGE = "L2_ORIGINAL"


def _geo_id(beam_id: str, source: str) -> str:
    tag = "O" if source == "ORIGINAL" else "R"
    return f"GEO::{tag}::{beam_id}"


def build_entry_from_l2_model(beam_model: Dict[str, Any]) -> Dict[str, Any]:
    """Create a geometry entry from an existing (ORIGINAL) L.2 BeamReinforcementModel."""
    beam_id = beam_model.get("beam_id", "UNKNOWN")
    geo = beam_model.get("geometry") or {}
    width = float(geo.get("width_mm") or 200)
    depth = float(geo.get("depth_mm") or 600)
    span = float(geo.get("clear_span_mm") or geo.get("effective_span_mm") or 3000)

    support_zones = beam_model.get("support_zones") or []
    support_locs = [
        {
            "support_id": sz.get("support_id", ""),
            "support_type": sz.get("support_type", ""),
            "position_fraction": sz.get("position_fraction", 0.0),
            "support_width_mm": sz.get("support_width_mm", 200.0),
        }
        for sz in support_zones
    ]

    return {
        "geometry_id": _geo_id(beam_id, "ORIGINAL"),
        "beam_id": beam_id,
        "source": "ORIGINAL",
        "creation_stage": _ORIGINAL_STAGE,
        "confidence": 1.0,
        "bounding_box": {
            "x_min": 0.0,
            "y_min": 0.0,
            "x_max": span,
            "y_max": depth,
            "width_mm": width,
            "depth_mm": depth,
        },
        "beam_axis": {
            "start_x": 0.0,
            "start_y": depth / 2.0,
            "end_x": span,
            "end_y": depth / 2.0,
            "length_mm": span,
        },
        "start_node": {"x": 0.0, "y": 0.0},
        "end_node": {"x": span, "y": 0.0},
        "support_locations": support_locs,
        "status": "PRESENT",
    }


def build_entry_recovered(
    beam_id: str,
    span_mm: float,
    width_mm: float,
    depth_mm: float,
    recovery_sources: List[str],
    confidence: float = 0.72,
    status: str = "RECOVERED",
) -> Dict[str, Any]:
    """Create a geometry entry for a beam whose geometry is being RECOVERED."""
    sup_width = 200.0

    return {
        "geometry_id": _geo_id(beam_id, "RECOVERED"),
        "beam_id": beam_id,
        "source": "RECOVERED",
        "creation_stage": _RECOVERY_STAGE,
        "confidence": round(confidence, 4),
        "bounding_box": {
            "x_min": 0.0,
            "y_min": 0.0,
            "x_max": span_mm,
            "y_max": depth_mm,
            "width_mm": width_mm,
            "depth_mm": depth_mm,
        },
        "beam_axis": {
            "start_x": 0.0,
            "start_y": depth_mm / 2.0,
            "end_x": span_mm,
            "end_y": depth_mm / 2.0,
            "length_mm": span_mm,
        },
        "start_node": {"x": 0.0, "y": 0.0},
        "end_node": {"x": span_mm, "y": 0.0},
        "support_locations": [
            {
                "support_id": f"SUP::REC::{beam_id}::LEFT",
                "support_type": "LEFT_SUPPORT",
                "position_fraction": 0.0,
                "support_width_mm": sup_width,
            },
            {
                "support_id": f"SUP::REC::{beam_id}::RIGHT",
                "support_type": "RIGHT_SUPPORT",
                "position_fraction": 1.0,
                "support_width_mm": sup_width,
            },
        ],
        "recovery_sources": recovery_sources,
        "status": status,
    }


def build_failed_entry(beam_id: str, reason: str) -> Dict[str, Any]:
    """Create a geometry entry for a beam where recovery FAILED."""
    return {
        "geometry_id": _geo_id(beam_id, "RECOVERED"),
        "beam_id": beam_id,
        "source": "RECOVERED",
        "creation_stage": _RECOVERY_STAGE,
        "confidence": 0.0,
        "bounding_box": None,
        "beam_axis": None,
        "start_node": None,
        "end_node": None,
        "support_locations": [],
        "failure_reason": reason,
        "status": "FAILED",
    }


class GeometryRegistry:
    """Manages geometry entries for all beams in the pipeline."""

    def __init__(self) -> None:
        self._entries: Dict[str, Dict[str, Any]] = {}

    def add(self, entry: Dict[str, Any]) -> None:
        beam_id = entry["beam_id"]
        self._entries[beam_id] = entry

    def get(self, beam_id: str) -> Optional[Dict[str, Any]]:
        return self._entries.get(beam_id)

    def has_geometry(self, beam_id: str) -> bool:
        e = self._entries.get(beam_id)
        return e is not None and e.get("status") != "FAILED"

    def all_entries(self) -> List[Dict[str, Any]]:
        return list(self._entries.values())

    def beam_ids(self) -> List[str]:
        return sorted(self._entries.keys(), key=lambda b: (len(b), b))

    def original_count(self) -> int:
        return sum(1 for e in self._entries.values() if e.get("source") == "ORIGINAL")

    def recovered_count(self) -> int:
        return sum(
            1 for e in self._entries.values()
            if e.get("source") == "RECOVERED" and e.get("status") == "RECOVERED"
        )

    def failed_count(self) -> int:
        return sum(1 for e in self._entries.values() if e.get("status") == "FAILED")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": len(self._entries),
            "original_count": self.original_count(),
            "recovered_count": self.recovered_count(),
            "failed_count": self.failed_count(),
            "beam_ids": self.beam_ids(),
            "entries": self.all_entries(),
        }
