"""Build beam-to-support connectivity graph."""

from __future__ import annotations

from typing import Any, List

from src.framing.beam_centerline_extractor import BeamCenterlineRecord
from src.framing.beam_support_detector import BeamSupportRecord


class BeamConnectivityBuilder:
    """Create graph relationships between beams and their supports."""

    def build(
        self,
        records: List[BeamCenterlineRecord],
        supports: List[BeamSupportRecord],
    ) -> dict[str, Any]:
        nodes = [
            {
                "beam_id": record.beam_id,
                "beam_mark": record.beam_mark,
                "has_centerline": record.segment is not None,
            }
            for record in records
        ]

        edges: List[dict[str, Any]] = []
        for support in supports:
            edges.append(
                {
                    "from_beam": support.beam_id,
                    "from_end": support.end,
                    "to": support.support_id or support.support_type,
                    "relationship": self._relationship(support.support_type),
                    "support_type": support.support_type,
                    "confidence": support.confidence,
                }
            )

        adjacency: dict[str, List[dict[str, Any]]] = {record.beam_id: [] for record in records}
        for edge in edges:
            adjacency.setdefault(edge["from_beam"], []).append(edge)
            if edge["support_type"] == "beam" and edge["to"] in adjacency:
                adjacency[edge["to"]].append(
                    {
                        **edge,
                        "from_beam": edge["to"],
                        "to": edge["from_beam"],
                        "relationship": "supported_by_beam",
                    }
                )

        return {
            "nodes": nodes,
            "edges": edges,
            "adjacency": adjacency,
            "edge_count": len(edges),
            "node_count": len(nodes),
        }

    @staticmethod
    def _relationship(support_type: str) -> str:
        mapping = {
            "column": "beam_to_column",
            "wall": "beam_to_wall",
            "beam": "beam_to_beam",
            "free_end": "beam_to_free_end",
        }
        return mapping.get(support_type, "beam_to_unknown")
