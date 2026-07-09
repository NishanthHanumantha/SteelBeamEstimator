"""Framing knowledge graph data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List


EDGE_CONNECTED_TO = "CONNECTED_TO"
EDGE_SUPPORTED_BY = "SUPPORTED_BY"
EDGE_INTERSECTS = "INTERSECTS"
EDGE_CONTINUOUS_WITH = "CONTINUOUS_WITH"
EDGE_USES_RULE = "USES_RULE"

NODE_BEAM = "BEAM"
NODE_BEAM_SECTION = "BEAM_SECTION"
NODE_ENGINEERING_LENGTH = "ENGINEERING_LENGTH"
NODE_SUPPORT = "SUPPORT"
NODE_ENGINEERING_RULES = "ENGINEERING_RULES"
NODE_COLUMN = "COLUMN"
NODE_WALL = "WALL"

PROJECT_RULES_ID = "PROJECT_RULES"


@dataclass
class GraphNode:
    id: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.type, **self.properties}


@dataclass
class GraphEdge:
    from_id: str
    to_id: str
    relationship: str
    confidence: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": self.from_id,
            "to": self.to_id,
            "relationship": self.relationship,
            "confidence": round(self.confidence, 4),
            **self.properties,
        }


@dataclass
class FramingKnowledgeGraph:
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        by_type: dict[str, List[dict[str, Any]]] = {}
        for node in self.nodes:
            by_type.setdefault(node.type, []).append(node.to_dict())
        return {
            "phase": "Phase F.5",
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "nodes": by_type,
            "edges": [edge.to_dict() for edge in self.edges],
        }

    def statistics(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for node in self.nodes:
            counts[node.type] = counts.get(node.type, 0) + 1
        rel_counts: dict[str, int] = {}
        for edge in self.edges:
            rel_counts[edge.relationship] = rel_counts.get(edge.relationship, 0) + 1
        return {"nodes": counts, "relationships": rel_counts}
