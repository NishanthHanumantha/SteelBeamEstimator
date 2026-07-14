"""
Topology Feature Extractor — connectivity and graph relationships.
Observations only. No semantic meaning assigned.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from engineering_feature_model import TopologyFeatures

# Multi-span groups from drawing topology
MULTI_SPAN_GROUPS: Dict[str, List[str]] = {
    "B8": ["B8", "B9", "B10"],
    "B9": ["B8", "B9", "B10"],
    "B10": ["B8", "B9", "B10"],
}


class TopologyFeatureExtractor:
    """Extract graph/connectivity observations from available beam data."""

    def extract(
        self,
        bar: Dict[str, Any],
        beam_model: Dict[str, Any],
        all_beam_models: List[Dict[str, Any]],
        engineering_objects: Optional[List[Dict[str, Any]]],
    ) -> TopologyFeatures:
        beam_id = bar.get("beam_id") or beam_model.get("beam_id") or ""
        group = MULTI_SPAN_GROUPS.get(beam_id, [])
        adjacent = [b for b in group if b != beam_id]

        # Engineering object references (from Phase G — read-only)
        connected_ids: List[str] = []
        graph_node_id = None
        if engineering_objects:
            for obj in engineering_objects:
                if str(obj.get("owner_context_id") or "").endswith(beam_id):
                    connected_ids.append(str(obj.get("object_id") or ""))
                    if not graph_node_id:
                        graph_node_id = str(obj.get("object_id") or "")

        # Support connections — support zone IDs from beam model
        support_ids: List[str] = []
        for sz in (beam_model.get("support_zones") or []):
            sup_id = sz.get("support_id")
            if sup_id:
                support_ids.append(sup_id)

        # Region membership — from L.2 engineering_notes and support_zones
        regions: List[str] = []
        for sz in (beam_model.get("support_zones") or []):
            st = sz.get("support_type")
            if st:
                regions.append(f"SUPPORT_REGION_{st}")
        if beam_id in MULTI_SPAN_GROUPS:
            regions.append("CONTINUOUS_MULTI_SPAN_REGION")

        # Intersection and crossing counts (estimated from bar's extent and adjacent beams)
        is_continuous = (bar.get("continuity") or "").upper()
        n_intersections = len(group) - 1 if "MULTI" in is_continuous else 0
        n_crossings = n_intersections

        return TopologyFeatures(
            connected_object_ids=connected_ids[:5],  # cap for readability
            parent_beam_id=beam_id,
            adjacent_beam_ids=adjacent,
            support_connection_ids=support_ids,
            intersection_count=n_intersections,
            crossing_count=n_crossings,
            region_membership=regions,
            engineering_graph_node_id=graph_node_id,
        )
