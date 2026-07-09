"""Phase F.3 — Resolve engineering beam supports from framing geometry."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from src.framing.beam_centerline_extractor import BeamCenterlineRecord
from src.framing.beam_geometry import LineSegment, Point2D
from src.framing.beam_support_detector import BeamSupportDetector, BeamSupportRecord
from src.framing.support_classifier import (
    SUPPORT_UNKNOWN,
    VALID_SUPPORT_TYPES,
    ClassifiedSupport,
    SupportClassifier,
)
from src.framing.support_graph import SupportGraphBuilder


class BeamSupportResolver:
    """Convert heuristic F.1 supports into engineering support models."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._enabled = bool(config.get("support_resolution", {}).get("enable", True))
        self._classifier = SupportClassifier(config)
        self._graph_builder = SupportGraphBuilder()
        self._stats: Dict[str, int] = {
            "columns": 0,
            "walls": 0,
            "beam_supports": 0,
            "slab_edges": 0,
            "free_ends": 0,
            "unknown": 0,
            "support_nodes": 0,
        }

    def resolve_model(
        self,
        model: dict[str, Any],
        records: List[BeamCenterlineRecord],
        structural_context: dict[str, Any],
        f1_supports: List[BeamSupportRecord],
    ) -> dict[str, Any]:
        if not self._enabled:
            logger.info("Support resolution disabled in config")
            return model

        columns = structural_context.get("columns", [])
        walls = structural_context.get("walls", [])
        slab_edges = self._extract_slab_edges(structural_context)
        beam_endpoints = self._beam_endpoints(records)
        f1_by_key = {(s.beam_id, s.end): s for s in f1_supports}

        for beam in model.get("beams", []):
            beam_id = beam["beam_id"]
            geometry = beam.get("geometry", {})
            centerline = geometry.get("centerline") or {}
            existing_supports = beam.get("supports", {})

            left_point = self._point_from_centerline(centerline, "start")
            right_point = self._point_from_centerline(centerline, "end")

            left = self._resolve_end(
                beam_id,
                left_point,
                columns,
                walls,
                slab_edges,
                beam_endpoints,
                f1_by_key.get((beam_id, "start")),
            )
            right = self._resolve_end(
                beam_id,
                right_point,
                columns,
                walls,
                slab_edges,
                beam_endpoints,
                f1_by_key.get((beam_id, "end")),
            )

            self._count_support(left)
            self._count_support(right)

            beam["supports"] = {
                "left": left.to_dict() if left else self._unknown_support(),
                "right": right.to_dict() if right else self._unknown_support(),
                "f1_records": existing_supports.get("records", []),
            }

        structural_nodes = self._graph_builder.build_structural_nodes(
            model.get("beams", []),
            columns,
        )
        support_graph = self._graph_builder.build(
            model.get("beams", []),
            structural_nodes,
        )

        self._stats["support_nodes"] = len(structural_nodes)
        model["structural_nodes"] = structural_nodes
        model["support_graph"] = support_graph
        model["connectivity_graph"] = self._engineering_connectivity_graph(support_graph)
        model["phase"] = "Phase F.3"
        model["model_version"] = "1.2"
        model["support_resolution_summary"] = dict(self._stats)

        logger.info(
            "Support resolution — nodes={}, columns={}, walls={}, beams={}, free_ends={}, unknown={}",
            self._stats["support_nodes"],
            self._stats["columns"],
            self._stats["walls"],
            self._stats["beam_supports"],
            self._stats["free_ends"],
            self._stats["unknown"],
        )
        return model

    def _resolve_end(
        self,
        beam_id: str,
        point: Optional[Point2D],
        columns: List[Any],
        walls: List[LineSegment],
        slab_edges: List[LineSegment],
        beam_endpoints: List[tuple],
        f1_support: Optional[BeamSupportRecord],
    ) -> Optional[ClassifiedSupport]:
        if point is None:
            return ClassifiedSupport(
                type=SUPPORT_UNKNOWN,
                id=None,
                distance_mm=0.0,
                source="GEOMETRY",
                confidence=0.0,
                point=Point2D(0.0, 0.0),
            )
        return self._classifier.classify_endpoint(
            beam_id,
            point,
            columns,
            walls,
            slab_edges,
            beam_endpoints,
            f1_support,
        )

    def _extract_slab_edges(self, structural_context: dict[str, Any]) -> List[LineSegment]:
        sr = self._config.get("support_resolution", {})
        slab_layers = set(SupportClassifier._layer_list(sr.get("slab_edge_layers", [])))
        if not slab_layers:
            return []
        walls: List[LineSegment] = []
        for entity in structural_context.get("entities", []):
            layer = str(entity.dxf.layer)
            if layer not in slab_layers:
                continue
            if entity.dxftype() == "LINE":
                start = entity.dxf.start
                end = entity.dxf.end
                handle = str(getattr(entity.dxf, "handle", "") or id(entity))
                walls.append(
                    LineSegment(
                        x1=float(start.x),
                        y1=float(start.y),
                        x2=float(end.x),
                        y2=float(end.y),
                        layer=layer,
                        handle=handle,
                        entity_ids=(handle,),
                    )
                )
        return walls

    def _engineering_connectivity_graph(self, support_graph: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase F.3",
            "description": "Support node ↔ beam structural graph",
            "node_count": support_graph.get("beam_node_count", 0)
            + support_graph.get("support_node_count", 0),
            "edge_count": support_graph.get("edge_count", 0),
            "nodes": support_graph.get("nodes", {}),
            "edges": support_graph.get("edges", []),
            "chains": support_graph.get("chains", []),
            "adjacency": support_graph.get("adjacency", {}),
        }

    def _count_support(self, support: Optional[ClassifiedSupport]) -> None:
        if support is None:
            self._stats["unknown"] += 1
            return
        mapping = {
            "COLUMN": "columns",
            "WALL": "walls",
            "BEAM": "beam_supports",
            "SLAB_EDGE": "slab_edges",
            "FREE_END": "free_ends",
            "UNKNOWN": "unknown",
        }
        key = mapping.get(support.type, "unknown")
        self._stats[key] += 1

    @staticmethod
    def _point_from_centerline(
        centerline: dict[str, Any], end: str
    ) -> Optional[Point2D]:
        key = "start_point" if end == "start" else "end_point"
        point = centerline.get(key)
        if not isinstance(point, dict):
            return None
        x, y = point.get("x"), point.get("y")
        if x is None or y is None:
            return None
        return Point2D(float(x), float(y))

    @staticmethod
    def _beam_endpoints(
        records: List[BeamCenterlineRecord],
    ) -> List[tuple[str, str, Point2D]]:
        endpoints: List[tuple[str, str, Point2D]] = []
        for record in records:
            if record.segment is None:
                continue
            endpoints.append((record.beam_id, "start", record.segment.start))
            endpoints.append((record.beam_id, "end", record.segment.end))
        return endpoints

    @staticmethod
    def _unknown_support() -> dict[str, Any]:
        return {
            "type": SUPPORT_UNKNOWN,
            "id": None,
            "distance_mm": 0.0,
            "source": "GEOMETRY",
            "confidence": 0.0,
        }

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)

    def validate_supports(self, model: dict[str, Any]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        beams = model.get("beams", [])

        with_model = sum(
            1
            for beam in beams
            if isinstance(beam.get("supports", {}).get("left"), dict)
            and isinstance(beam.get("supports", {}).get("right"), dict)
        )
        checks.append(
            {
                "name": "Support Model",
                "status": "PASS" if with_model == len(beams) and with_model > 0 else "FAIL",
                "with_model": with_model,
                "total": len(beams),
            }
        )

        invalid_types = 0
        missing_confidence = 0
        for beam in beams:
            for end in ("left", "right"):
                support = beam.get("supports", {}).get(end, {})
                if support.get("type") not in VALID_SUPPORT_TYPES:
                    invalid_types += 1
                if support.get("confidence") is None:
                    missing_confidence += 1

        checks.append(
            {
                "name": "Support Types",
                "status": "PASS" if invalid_types == 0 else "FAIL",
                "invalid_types": invalid_types,
            }
        )
        checks.append(
            {
                "name": "Support Confidence",
                "status": "PASS" if missing_confidence == 0 else "FAIL",
                "missing_confidence": missing_confidence,
            }
        )

        node_count = len(model.get("structural_nodes", []))
        checks.append(
            {
                "name": "Structural Nodes",
                "status": "PASS" if node_count > 0 else "FAIL",
                "node_count": node_count,
            }
        )

        graph_edges = model.get("support_graph", {}).get("edge_count", 0)
        checks.append(
            {
                "name": "Support Graph",
                "status": "PASS" if graph_edges >= len(beams) else "FAIL",
                "edge_count": graph_edges,
            }
        )

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase F.3",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
            },
        }
