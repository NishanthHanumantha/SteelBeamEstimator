"""
T1.7 graph models + renderer contract API.
MODEL_VERSION: 9.4.0
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

MODEL_VERSION = "9.4.0"
PHASE_ID = "T1.7"

# Extensible node type registry
NODE_TYPES = frozenset(
    {
        "Beam",
        "PhysicalBar",
        "Leader",
        "LeaderArrow",
        "LeaderTarget",
        "Annotation",
        "Dimension",
        "Text",
        "SemanticFact",
        "Support",
        "DevelopmentLength",
        "StirrupNote",
        "SideFaceReinforcement",
        "SpacerBar",
        "OwnedEntity",
    }
)

# Explicit edge predicates
EDGE_TYPES = frozenset(
    {
        "OWNS",
        "POINTS_TO",
        "ATTACHED_TO",
        "DESCRIBES",
        "INTERPRETS",
        "MEASURES",
        "ANCHORS",
        "PROPAGATES_TO",
        "HAS_ARROW",
        "TARGETS",
        "MATCHES_ENTITY",
        "NEAR",
    }
)

CONFIDENCE_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNKNOWN": 0}


def make_node(
    node_id: str,
    node_type: str,
    beam_id: Optional[str],
    *,
    source: str,
    confidence: str = "HIGH",
    attributes: Optional[Dict[str, Any]] = None,
    relationships: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        "id": node_id,
        "type": node_type,
        "beam_id": beam_id,
        "confidence": confidence,
        "source": source,
        "attributes": attributes or {},
        "relationships": relationships or [],
    }


def make_edge(
    edge_id: str,
    edge_type: str,
    source_id: str,
    target_id: str,
    *,
    beam_id: Optional[str],
    confidence: str,
    reason: str,
    evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "id": edge_id,
        "type": edge_type,
        "source_id": source_id,
        "target_id": target_id,
        "beam_id": beam_id,
        "confidence": confidence,
        "reason": reason,
        "evidence": evidence or {},
    }


class AnnotationGraph:
    """
    In-memory annotation graph with the renderer contract API.

    Future renderer / Vision stages should call these methods rather than
    reading raw DXF or inventing proximity heuristics.
    """

    def __init__(self, payload: Optional[Dict[str, Any]] = None):
        payload = payload or {}
        self.phase_id = payload.get("phase_id") or PHASE_ID
        self.model_version = payload.get("model_version") or MODEL_VERSION
        self.nodes: Dict[str, Dict[str, Any]] = {
            n["id"]: n for n in (payload.get("nodes") or []) if n.get("id")
        }
        self.edges: List[Dict[str, Any]] = list(payload.get("edges") or [])
        self.meta: Dict[str, Any] = dict(payload.get("meta") or {})
        self._index_edges()

    def _index_edges(self) -> None:
        self._out: Dict[str, List[Dict[str, Any]]] = {}
        self._in: Dict[str, List[Dict[str, Any]]] = {}
        for e in self.edges:
            self._out.setdefault(e["source_id"], []).append(e)
            self._in.setdefault(e["target_id"], []).append(e)
        # Mirror relationships onto nodes for JSON consumers
        for nid, node in self.nodes.items():
            rels = []
            for e in self._out.get(nid, []):
                rels.append(
                    {
                        "edge_id": e["id"],
                        "type": e["type"],
                        "direction": "out",
                        "other_id": e["target_id"],
                        "confidence": e["confidence"],
                        "reason": e["reason"],
                    }
                )
            for e in self._in.get(nid, []):
                rels.append(
                    {
                        "edge_id": e["id"],
                        "type": e["type"],
                        "direction": "in",
                        "other_id": e["source_id"],
                        "confidence": e["confidence"],
                        "reason": e["reason"],
                    }
                )
            node["relationships"] = rels

    def add_node(self, node: Dict[str, Any]) -> None:
        self.nodes[node["id"]] = node

    def add_edge(self, edge: Dict[str, Any]) -> None:
        self.edges.append(edge)

    def finalize(self) -> None:
        self._index_edges()

    # --- Renderer contract -------------------------------------------------

    def get_beam_annotations(self, beam_id: str) -> List[Dict[str, Any]]:
        return [
            n
            for n in self.nodes.values()
            if n.get("beam_id") == beam_id
            and n.get("type")
            in (
                "Annotation",
                "Text",
                "Dimension",
                "StirrupNote",
                "SideFaceReinforcement",
                "DevelopmentLength",
            )
        ]

    def get_physical_bars(self, beam_id: str) -> List[Dict[str, Any]]:
        return [
            n
            for n in self.nodes.values()
            if n.get("beam_id") == beam_id and n.get("type") == "PhysicalBar"
        ]

    def get_semantic_annotations(self, beam_id: str) -> List[Dict[str, Any]]:
        return [
            n
            for n in self.nodes.values()
            if n.get("beam_id") == beam_id
            and n.get("type")
            in (
                "SemanticFact",
                "StirrupNote",
                "SideFaceReinforcement",
                "DevelopmentLength",
                "SpacerBar",
            )
        ]

    def get_render_entities(self, beam_id: str) -> List[Dict[str, Any]]:
        """
        Handles / entity refs that should be drawn for this beam.

        Prefer T1.6 OwnedEntity HIGH nodes, then any entity handles attached
        via MATCHES_ENTITY / DESCRIBES / POINTS_TO chains.
        """
        handles: Dict[str, Dict[str, Any]] = {}
        for n in self.nodes.values():
            if n.get("beam_id") != beam_id:
                continue
            if n.get("type") == "OwnedEntity":
                h = (n.get("attributes") or {}).get("handle")
                if h:
                    handles[str(h).upper()] = {
                        "handle": str(h).upper(),
                        "source_node": n["id"],
                        "ownership": (n.get("attributes") or {}).get("ownership"),
                        "role": (n.get("attributes") or {}).get("role"),
                        "via": "OwnedEntity",
                    }
            attrs = n.get("attributes") or {}
            for key in ("handle", "entity_handle", "dxf_handle"):
                if attrs.get(key):
                    h = str(attrs[key]).upper()
                    handles.setdefault(
                        h,
                        {
                            "handle": h,
                            "source_node": n["id"],
                            "via": n.get("type"),
                        },
                    )
        # Walk annotation → leader → bar entity handles
        for ann in self.get_beam_annotations(beam_id):
            for e in self._out.get(ann["id"], []):
                if e["type"] in ("ATTACHED_TO", "DESCRIBES"):
                    other = self.nodes.get(e["target_id"])
                    if not other:
                        continue
                    ah = (other.get("attributes") or {}).get("handle")
                    if ah:
                        handles.setdefault(
                            str(ah).upper(),
                            {
                                "handle": str(ah).upper(),
                                "source_node": other["id"],
                                "via": f"from_{ann['id']}",
                            },
                        )
        return sorted(handles.values(), key=lambda r: r["handle"])

    def get_leaders(self, beam_id: str) -> List[Dict[str, Any]]:
        return [
            n
            for n in self.nodes.values()
            if n.get("beam_id") == beam_id and n.get("type") == "Leader"
        ]

    def nodes_of_type(self, beam_id: str, node_type: str) -> List[Dict[str, Any]]:
        return [
            n
            for n in self.nodes.values()
            if n.get("beam_id") == beam_id and n.get("type") == node_type
        ]

    def neighbors(
        self, node_id: str, edge_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        out = []
        for e in self._out.get(node_id, []) + self._in.get(node_id, []):
            if edge_type and e["type"] != edge_type:
                continue
            other_id = e["target_id"] if e["source_id"] == node_id else e["source_id"]
            other = self.nodes.get(other_id)
            if other:
                out.append({"edge": e, "node": other})
        return out

    def to_dict(self) -> Dict[str, Any]:
        self.finalize()
        by_beam: Dict[str, Dict[str, Any]] = {}
        for n in self.nodes.values():
            bid = n.get("beam_id") or "_unassigned"
            slot = by_beam.setdefault(
                bid,
                {
                    "beam_id": bid,
                    "node_ids": [],
                    "annotation_ids": [],
                    "physical_bar_ids": [],
                    "leader_ids": [],
                    "semantic_ids": [],
                },
            )
            slot["node_ids"].append(n["id"])
            t = n.get("type")
            if t in (
                "Annotation",
                "Text",
                "Dimension",
                "StirrupNote",
                "SideFaceReinforcement",
                "DevelopmentLength",
            ):
                slot["annotation_ids"].append(n["id"])
            if t == "PhysicalBar":
                slot["physical_bar_ids"].append(n["id"])
            if t == "Leader":
                slot["leader_ids"].append(n["id"])
            if t in (
                "SemanticFact",
                "StirrupNote",
                "SideFaceReinforcement",
                "DevelopmentLength",
                "SpacerBar",
            ):
                slot["semantic_ids"].append(n["id"])

        return {
            "phase_id": self.phase_id,
            "model_version": self.model_version,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "beam_count": len([b for b in by_beam if b != "_unassigned"]),
            "meta": self.meta,
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
            "by_beam": by_beam,
            "api": {
                "get_beam_annotations": "AnnotationGraph.get_beam_annotations(beam_id)",
                "get_physical_bars": "AnnotationGraph.get_physical_bars(beam_id)",
                "get_render_entities": "AnnotationGraph.get_render_entities(beam_id)",
                "get_semantic_annotations": "AnnotationGraph.get_semantic_annotations(beam_id)",
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnnotationGraph":
        return cls(data)
