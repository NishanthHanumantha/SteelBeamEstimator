"""Classify reinforcement assets into G.5.1 engineering object types."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.reinforcement.engineering_object_types import (
    CLASSIFICATION_SOURCE_GEOMETRY,
    CLASSIFICATION_SOURCE_GEOMETRY_AND_TEXT,
    CLASSIFICATION_SOURCE_INFERRED,
    CLASSIFICATION_SOURCE_LEADER,
    CLASSIFICATION_SOURCE_TEXT,
    G51_OBJECT_TYPES,
    OBJECT_TYPE_ANCHORAGE,
    OBJECT_TYPE_BEAM_LABEL,
    OBJECT_TYPE_BOTTOM_BAR,
    OBJECT_TYPE_BOTTOM_EXTRA_BAR,
    OBJECT_TYPE_DEVELOPMENT_LENGTH,
    OBJECT_TYPE_DIMENSION,
    OBJECT_TYPE_HOOK,
    OBJECT_TYPE_REINFORCEMENT_NOTE,
    OBJECT_TYPE_SIDE_FACE_REINFORCEMENT,
    OBJECT_TYPE_SPACER_BAR,
    OBJECT_TYPE_STIRRUP,
    OBJECT_TYPE_TOP_BAR,
    OBJECT_TYPE_TOP_EXTRA_BAR,
    OBJECT_TYPE_UNKNOWN,
)

BEAM_LABEL_RE = re.compile(r"^B\d+\s*\(", re.IGNORECASE)
BAR_NOTATION_RE = re.compile(r"^\d+[- ]?Y\d+", re.IGNORECASE)
STIRRUP_NOTATION_RE = re.compile(r"@|Y\d+@", re.IGNORECASE)
NUMERIC_DIMENSION_RE = re.compile(r"^\d+(?:\.\d+)?$")
LD_RE = re.compile(r"^LD\b", re.IGNORECASE)


@dataclass
class AssetClassification:
    asset_id: str
    asset_kind: str
    object_type: str
    confidence: float
    classification_source: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ObjectRoleBucket:
    object_type: str
    geometry: List[str] = field(default_factory=list)
    text: List[str] = field(default_factory=list)
    leaders: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    confidence: float = 0.0
    classification_source: str = CLASSIFICATION_SOURCE_INFERRED
    metadata: Dict[str, Any] = field(default_factory=dict)


class EngineeringObjectClassifier:
    """Classify owned geometry and annotations into engineering object roles."""

    def __init__(self, leader_link_tolerance_mm: float = 2500.0) -> None:
        self._leader_link_tolerance_mm = leader_link_tolerance_mm

    def classify_erc(
        self,
        erc: dict[str, Any],
        sketches: List[dict[str, Any]],
        text_objects: List[dict[str, Any]],
        leaders: List[dict[str, Any]],
        blocks: List[dict[str, Any]],
        views: List[dict[str, Any]],
    ) -> Tuple[List[AssetClassification], List[ObjectRoleBucket]]:
        beam_mark = str(erc.get("beam_mark", "")).upper()
        owned_sketch_ids = set(erc.get("owned_geometry", []))
        owned_text_ids = set(erc.get("owned_text", []))
        owned_leader_ids = set(erc.get("owned_leaders", []))
        owned_block_ids = set(erc.get("owned_blocks", []))

        sketch_by_id = {s["geometry_id"]: s for s in sketches if s.get("geometry_id") in owned_sketch_ids}
        text_by_id = {t["geometry_id"]: t for t in text_objects if t.get("geometry_id") in owned_text_ids}
        leader_by_id = {l["geometry_id"]: l for l in leaders if l.get("geometry_id") in owned_leader_ids}
        block_by_id = {b["geometry_id"]: b for b in blocks if b.get("geometry_id") in owned_block_ids}

        view_center_y = self._view_center_y(views, erc.get("owned_views", []))
        leader_to_text = self._link_leaders_to_text(leader_by_id, text_by_id)

        asset_classes: List[AssetClassification] = []
        assigned: Dict[str, str] = {}

        for sketch_id, sketch in sketch_by_id.items():
            cls = self._classify_sketch(sketch, view_center_y)
            asset_classes.append(cls)
            assigned[sketch_id] = cls.object_type

        for text_id, text in text_by_id.items():
            cls = self._classify_text(text, beam_mark, view_center_y)
            asset_classes.append(cls)
            assigned[text_id] = cls.object_type

        for leader_id in leader_by_id:
            linked_text = leader_to_text.get(leader_id)
            if linked_text and linked_text in assigned:
                object_type = assigned[linked_text]
                source = CLASSIFICATION_SOURCE_LEADER
                asset_classes.append(
                    AssetClassification(
                        asset_id=leader_id,
                        asset_kind="leader",
                        object_type=object_type,
                        confidence=0.85,
                        classification_source=source,
                        metadata={"linked_text": linked_text},
                    )
                )
                assigned[leader_id] = object_type

        buckets = self._aggregate_into_roles(
            sketch_by_id,
            text_by_id,
            leader_by_id,
            block_by_id,
            asset_classes,
            assigned,
            leader_to_text,
            view_center_y,
        )
        return asset_classes, buckets

    def _view_center_y(self, views: List[dict[str, Any]], owned_view_ids: List[str]) -> float:
        boxes = []
        view_ids = set(owned_view_ids)
        for view in views:
            vid = view.get("view_id", view.get("geometry_id"))
            if vid in view_ids:
                box = view.get("bbox", {})
                if box:
                    boxes.append(box)
        if not boxes:
            return 0.0
        min_y = min(b.get("min_y", 0.0) for b in boxes)
        max_y = max(b.get("max_y", 0.0) for b in boxes)
        return (min_y + max_y) / 2.0

    @staticmethod
    def _text_center_y(text: dict[str, Any]) -> float:
        box = text.get("bbox", {})
        return (float(box.get("min_y", 0.0)) + float(box.get("max_y", 0.0))) / 2.0

    @staticmethod
    def _sketch_center_y(sketch: dict[str, Any]) -> float:
        box = sketch.get("bbox", {})
        return (float(box.get("min_y", 0.0)) + float(box.get("max_y", 0.0))) / 2.0

    def _classify_sketch(self, sketch: dict[str, Any], view_center_y: float) -> AssetClassification:
        sketch_id = str(sketch.get("geometry_id", ""))
        sketch_type = str(sketch.get("type", "")).upper()
        center_y = self._sketch_center_y(sketch)

        if sketch_type == "STIRRUP":
            return AssetClassification(
                sketch_id, "geometry", OBJECT_TYPE_STIRRUP, 0.95, CLASSIFICATION_SOURCE_GEOMETRY
            )
        if sketch_type == "CROSS_SECTION":
            return AssetClassification(
                sketch_id,
                "geometry",
                OBJECT_TYPE_STIRRUP,
                0.9,
                CLASSIFICATION_SOURCE_GEOMETRY,
                {"section_view": True},
            )
        if sketch_type == "TYPICAL_DETAIL":
            return AssetClassification(
                sketch_id,
                "geometry",
                OBJECT_TYPE_STIRRUP,
                0.86,
                CLASSIFICATION_SOURCE_GEOMETRY,
                {"typical_detail": True},
            )
        if sketch_type == "LONGITUDINAL":
            object_type = (
                OBJECT_TYPE_TOP_BAR if center_y < view_center_y else OBJECT_TYPE_BOTTOM_BAR
            )
            return AssetClassification(
                sketch_id, "geometry", object_type, 0.88, CLASSIFICATION_SOURCE_GEOMETRY
            )
        return AssetClassification(
            sketch_id, "geometry", OBJECT_TYPE_UNKNOWN, 0.5, CLASSIFICATION_SOURCE_GEOMETRY
        )

    def _classify_text(
        self,
        text: dict[str, Any],
        beam_mark: str,
        view_center_y: float,
    ) -> AssetClassification:
        text_id = str(text.get("geometry_id", ""))
        raw = str(text.get("text", "")).strip()
        upper = raw.upper()
        center_y = self._text_center_y(text)

        if LD_RE.search(upper):
            return AssetClassification(
                text_id, "text", OBJECT_TYPE_DEVELOPMENT_LENGTH, 0.97, CLASSIFICATION_SOURCE_TEXT
            )
        if "SIDE FACE" in upper or "SIDE.FACE" in upper or "SFR" in upper:
            return AssetClassification(
                text_id,
                "text",
                OBJECT_TYPE_SIDE_FACE_REINFORCEMENT,
                0.96,
                CLASSIFICATION_SOURCE_TEXT,
            )
        if "SPACER" in upper:
            return AssetClassification(
                text_id, "text", OBJECT_TYPE_SPACER_BAR, 0.94, CLASSIFICATION_SOURCE_TEXT
            )
        if "HOOK" in upper:
            return AssetClassification(
                text_id, "text", OBJECT_TYPE_HOOK, 0.9, CLASSIFICATION_SOURCE_TEXT
            )
        if "ANCHOR" in upper:
            return AssetClassification(
                text_id, "text", OBJECT_TYPE_ANCHORAGE, 0.9, CLASSIFICATION_SOURCE_TEXT
            )
        if BEAM_LABEL_RE.match(raw):
            if beam_mark and beam_mark in upper.replace(" ", ""):
                return AssetClassification(
                    text_id, "text", OBJECT_TYPE_BEAM_LABEL, 0.98, CLASSIFICATION_SOURCE_TEXT
                )
            return AssetClassification(
                text_id,
                "text",
                OBJECT_TYPE_REINFORCEMENT_NOTE,
                0.8,
                CLASSIFICATION_SOURCE_TEXT,
                {"adjacent_beam_label": True},
            )
        if NUMERIC_DIMENSION_RE.match(raw):
            return AssetClassification(
                text_id, "text", OBJECT_TYPE_DIMENSION, 0.92, CLASSIFICATION_SOURCE_TEXT
            )
        if STIRRUP_NOTATION_RE.search(upper):
            return AssetClassification(
                text_id, "text", OBJECT_TYPE_STIRRUP, 0.93, CLASSIFICATION_SOURCE_TEXT
            )
        if BAR_NOTATION_RE.match(raw):
            if "EXTRA" in upper and "TOP" in upper:
                return AssetClassification(
                    text_id, "text", OBJECT_TYPE_TOP_EXTRA_BAR, 0.94, CLASSIFICATION_SOURCE_TEXT
                )
            if "EXTRA" in upper and "BOTTOM" in upper:
                return AssetClassification(
                    text_id, "text", OBJECT_TYPE_BOTTOM_EXTRA_BAR, 0.94, CLASSIFICATION_SOURCE_TEXT
                )
            if "EXTRA" in upper:
                role = (
                    OBJECT_TYPE_TOP_EXTRA_BAR
                    if center_y < view_center_y
                    else OBJECT_TYPE_BOTTOM_EXTRA_BAR
                )
                return AssetClassification(
                    text_id, "text", role, 0.9, CLASSIFICATION_SOURCE_TEXT
                )
            role = OBJECT_TYPE_TOP_BAR if center_y < view_center_y else OBJECT_TYPE_BOTTOM_BAR
            return AssetClassification(
                text_id, "text", role, 0.9, CLASSIFICATION_SOURCE_TEXT
            )
        if upper.startswith("NOTE") or "DETAIL" in upper or "REFER" in upper:
            return AssetClassification(
                text_id, "text", OBJECT_TYPE_REINFORCEMENT_NOTE, 0.75, CLASSIFICATION_SOURCE_TEXT
            )
        return AssetClassification(
            text_id, "text", OBJECT_TYPE_UNKNOWN, 0.4, CLASSIFICATION_SOURCE_TEXT
        )

    def _link_leaders_to_text(
        self,
        leaders: Dict[str, dict[str, Any]],
        texts: Dict[str, dict[str, Any]],
    ) -> Dict[str, str]:
        links: Dict[str, str] = {}
        for leader_id, leader in leaders.items():
            end = leader.get("end", leader.get("arrow_head", {}))
            if not end:
                continue
            ex = float(end.get("x", 0.0))
            ey = float(end.get("y", 0.0))
            best_id = ""
            best_dist = self._leader_link_tolerance_mm
            for text_id, text in texts.items():
                box = text.get("bbox", {})
                cx = (float(box.get("min_x", 0.0)) + float(box.get("max_x", 0.0))) / 2.0
                cy = (float(box.get("min_y", 0.0)) + float(box.get("max_y", 0.0))) / 2.0
                dist = ((ex - cx) ** 2 + (ey - cy) ** 2) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    best_id = text_id
            if best_id:
                links[leader_id] = best_id
        return links

    def _aggregate_into_roles(
        self,
        sketch_by_id: Dict[str, dict[str, Any]],
        text_by_id: Dict[str, dict[str, Any]],
        leader_by_id: Dict[str, dict[str, Any]],
        block_by_id: Dict[str, dict[str, Any]],
        asset_classes: List[AssetClassification],
        assigned: Dict[str, str],
        leader_to_text: Dict[str, str],
        view_center_y: float,
    ) -> List[ObjectRoleBucket]:
        by_type_assets: Dict[str, Dict[str, List[str]]] = {}
        confidences: Dict[str, List[float]] = {}
        sources: Dict[str, set[str]] = {}

        def add_asset(object_type: str, kind: str, asset_id: str, confidence: float, source: str) -> None:
            if object_type not in G51_OBJECT_TYPES:
                object_type = OBJECT_TYPE_UNKNOWN
            bucket = by_type_assets.setdefault(
                object_type,
                {"geometry": [], "text": [], "leaders": [], "blocks": []},
            )
            key = "geometry" if kind == "geometry" else kind + "s" if kind != "text" else "text"
            if kind == "block":
                key = "blocks"
            if kind == "leader":
                key = "leaders"
            if asset_id not in bucket[key]:
                bucket[key].append(asset_id)
            confidences.setdefault(object_type, []).append(confidence)
            sources.setdefault(object_type, set()).add(source)

        for cls in asset_classes:
            add_asset(cls.object_type, cls.asset_kind, cls.asset_id, cls.confidence, cls.classification_source)

        for leader_id in leader_by_id:
            if leader_id in assigned:
                continue
            linked = leader_to_text.get(leader_id)
            if linked and linked in assigned:
                add_asset(assigned[linked], "leader", leader_id, 0.85, CLASSIFICATION_SOURCE_GEOMETRY_AND_TEXT)

        for block_id in block_by_id:
            add_asset(OBJECT_TYPE_UNKNOWN, "block", block_id, 0.5, CLASSIFICATION_SOURCE_GEOMETRY)

        buckets: List[ObjectRoleBucket] = []
        stirrup_geom = [
            sid
            for sid, sketch in sketch_by_id.items()
            if assigned.get(sid) == OBJECT_TYPE_STIRRUP
        ]
        stirrup_text = [
            tid for tid in text_by_id if assigned.get(tid) == OBJECT_TYPE_STIRRUP
        ]
        if len(stirrup_geom) > 1:
            for idx, sid in enumerate(stirrup_geom, start=1):
                buckets.append(
                    ObjectRoleBucket(
                        object_type=OBJECT_TYPE_STIRRUP,
                        geometry=[sid],
                        confidence=0.9,
                        classification_source=CLASSIFICATION_SOURCE_GEOMETRY,
                        metadata={"zone_index": idx},
                    )
                )
            if stirrup_text:
                buckets.append(
                    ObjectRoleBucket(
                        object_type=OBJECT_TYPE_STIRRUP,
                        text=stirrup_text,
                        confidence=0.9,
                        classification_source=CLASSIFICATION_SOURCE_TEXT,
                    )
                )
            by_type_assets.pop(OBJECT_TYPE_STIRRUP, None)
        elif len(stirrup_geom) == 1 and stirrup_text:
            buckets.append(
                ObjectRoleBucket(
                    object_type=OBJECT_TYPE_STIRRUP,
                    geometry=stirrup_geom,
                    text=stirrup_text,
                    confidence=0.93,
                    classification_source=CLASSIFICATION_SOURCE_GEOMETRY_AND_TEXT,
                )
            )
            by_type_assets.pop(OBJECT_TYPE_STIRRUP, None)

        for object_type, refs in by_type_assets.items():
            if not any(refs.values()):
                continue
            avg_conf = sum(confidences.get(object_type, [0.5])) / max(
                len(confidences.get(object_type, [0.5])), 1
            )
            srcs = sources.get(object_type, {CLASSIFICATION_SOURCE_INFERRED})
            if len(srcs) > 1:
                source = CLASSIFICATION_SOURCE_GEOMETRY_AND_TEXT
            else:
                source = next(iter(srcs))
            buckets.append(
                ObjectRoleBucket(
                    object_type=object_type,
                    geometry=list(refs["geometry"]),
                    text=list(refs["text"]),
                    leaders=list(refs["leaders"]),
                    blocks=list(refs["blocks"]),
                    confidence=round(avg_conf, 2),
                    classification_source=source,
                )
            )

        if not buckets:
            buckets.append(ObjectRoleBucket(object_type=OBJECT_TYPE_UNKNOWN))

        return buckets
