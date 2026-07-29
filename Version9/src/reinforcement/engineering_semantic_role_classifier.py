"""Classify reinforcement assets into Engineering Semantic Roles."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.reinforcement.engineering_semantic_role_lifecycle import (
    EngineeringSemanticRoleLifecycle,
)
from src.reinforcement.engineering_semantic_role_types import (
    CLASSIFICATION_SOURCE_GEOMETRY,
    CLASSIFICATION_SOURCE_GEOMETRY_AND_TEXT,
    CLASSIFICATION_SOURCE_LEADER,
    CLASSIFICATION_SOURCE_TEXT,
    ROLE_ANCHORAGE,
    ROLE_BEAM_IDENTIFIER,
    ROLE_CALLOUT,
    ROLE_DEVELOPMENT_LENGTH,
    ROLE_DIMENSION,
    ROLE_GENERAL_NOTE,
    ROLE_HOOK,
    ROLE_LEADER,
    ROLE_LONGITUDINAL,
    ROLE_SECTION_IDENTIFIER,
    ROLE_SIDE_FACE,
    ROLE_SPACER,
    ROLE_TRANSVERSE,
    ROLE_UNKNOWN,
    VALID_SEMANTIC_ROLE_TYPES,
)

BEAM_LABEL_RE = re.compile(r"^B\d+\s*\(", re.IGNORECASE)
LONGITUDINAL_BAR_RE = re.compile(r"^\d+[- ]?Y\d+", re.IGNORECASE)
TRANSVERSE_BAR_RE = re.compile(r"@|Y\d+@|\d+L[- ]?Y\d+", re.IGNORECASE)
NUMERIC_DIMENSION_RE = re.compile(r"^\d+(?:\.\d+)?$")
LD_RE = re.compile(r"^LD\b|DEVELOPMENT", re.IGNORECASE)


@dataclass
class SemanticAssetClassification:
    asset_id: str
    asset_kind: str
    role_type: str
    confidence: float
    classification_source: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticRoleBucket:
    role_type: str
    geometry: List[str] = field(default_factory=list)
    text: List[str] = field(default_factory=list)
    leaders: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    confidence: float = 0.0
    classification_source: str = CLASSIFICATION_SOURCE_GEOMETRY
    metadata: Dict[str, Any] = field(default_factory=dict)


class EngineeringSemanticRoleClassifier:
    """Assign semantic meaning to geometry and annotations — no top/bottom decisions."""

    def __init__(self, leader_link_tolerance_mm: float = 2500.0) -> None:
        self._leader_link_tolerance_mm = leader_link_tolerance_mm

    def classify_erc(
        self,
        erc: dict[str, Any],
        sketches: List[dict[str, Any]],
        text_objects: List[dict[str, Any]],
        leaders: List[dict[str, Any]],
        blocks: List[dict[str, Any]],
    ) -> Tuple[List[SemanticAssetClassification], List[SemanticRoleBucket]]:
        owned_geometry = set(erc.get("owned_geometry", []))
        owned_text = set(erc.get("owned_text", []))
        owned_leaders = set(erc.get("owned_leaders", []))
        owned_blocks = set(erc.get("owned_blocks", []))

        sketch_by_id = {
            s["geometry_id"]: s for s in sketches if s.get("geometry_id") in owned_geometry
        }
        text_by_id = {
            t["geometry_id"]: t for t in text_objects if t.get("geometry_id") in owned_text
        }
        leader_by_id = {
            l["geometry_id"]: l for l in leaders if l.get("geometry_id") in owned_leaders
        }
        block_by_id = {
            b["geometry_id"]: b for b in blocks if b.get("geometry_id") in owned_blocks
        }

        leader_to_text = self._link_leaders_to_text(leader_by_id, text_by_id)
        asset_classes: List[SemanticAssetClassification] = []
        assigned: Dict[str, str] = {}

        for sketch_id, sketch in sketch_by_id.items():
            cls = self._classify_sketch(sketch)
            asset_classes.append(cls)
            assigned[sketch_id] = cls.role_type

        for text_id, text in text_by_id.items():
            cls = self._classify_text(text)
            asset_classes.append(cls)
            assigned[text_id] = cls.role_type

        for leader_id, leader in leader_by_id.items():
            linked = leader_to_text.get(leader_id)
            if linked and linked in assigned:
                role_type = assigned[linked]
                source = CLASSIFICATION_SOURCE_LEADER
            else:
                role_type = ROLE_LEADER
                source = CLASSIFICATION_SOURCE_LEADER
            asset_classes.append(
                SemanticAssetClassification(
                    leader_id, "leader", role_type, 0.85, source
                )
            )
            assigned[leader_id] = role_type

        for block_id in block_by_id:
            asset_classes.append(
                SemanticAssetClassification(
                    block_id, "block", ROLE_CALLOUT, 0.5, CLASSIFICATION_SOURCE_GEOMETRY
                )
            )
            assigned[block_id] = ROLE_CALLOUT

        buckets = self._aggregate(asset_classes, assigned, leader_to_text)
        return asset_classes, buckets

    def _classify_sketch(self, sketch: dict[str, Any]) -> SemanticAssetClassification:
        sketch_id = str(sketch.get("geometry_id", ""))
        sketch_type = str(sketch.get("type", "")).upper()
        layers = [str(layer).upper() for layer in sketch.get("layers", [])]

        if sketch_type in ("STIRRUP", "CROSS_SECTION", "TYPICAL_DETAIL"):
            return SemanticAssetClassification(
                sketch_id, "geometry", ROLE_TRANSVERSE, 0.92, CLASSIFICATION_SOURCE_GEOMETRY
            )
        if sketch_type == "LONGITUDINAL":
            return SemanticAssetClassification(
                sketch_id,
                "geometry",
                ROLE_LONGITUDINAL,
                0.9,
                CLASSIFICATION_SOURCE_GEOMETRY,
            )
        if any("HOOK" in layer for layer in layers):
            return SemanticAssetClassification(
                sketch_id, "geometry", ROLE_HOOK, 0.85, CLASSIFICATION_SOURCE_GEOMETRY
            )
        return SemanticAssetClassification(
            sketch_id, "geometry", ROLE_CALLOUT, 0.55, CLASSIFICATION_SOURCE_GEOMETRY
        )

    def _classify_text(self, text: dict[str, Any]) -> SemanticAssetClassification:
        text_id = str(text.get("geometry_id", ""))
        raw = str(text.get("text", "")).strip()
        upper = raw.upper()
        layer = str(text.get("layer", "")).upper()

        if LD_RE.search(upper):
            return SemanticAssetClassification(
                text_id, "text", ROLE_DEVELOPMENT_LENGTH, 0.97, CLASSIFICATION_SOURCE_TEXT
            )
        if "SIDE FACE" in upper or "SIDE.FACE" in upper or "SFR" in upper:
            return SemanticAssetClassification(
                text_id, "text", ROLE_SIDE_FACE, 0.96, CLASSIFICATION_SOURCE_TEXT
            )
        if "SPACER" in upper or "CHAIR" in upper:
            return SemanticAssetClassification(
                text_id, "text", ROLE_SPACER, 0.94, CLASSIFICATION_SOURCE_TEXT
            )
        if "HOOK" in upper:
            return SemanticAssetClassification(
                text_id, "text", ROLE_HOOK, 0.9, CLASSIFICATION_SOURCE_TEXT
            )
        if "ANCHOR" in upper or "EMBEDMENT" in upper:
            return SemanticAssetClassification(
                text_id, "text", ROLE_ANCHORAGE, 0.9, CLASSIFICATION_SOURCE_TEXT
            )
        if BEAM_LABEL_RE.match(raw):
            return SemanticAssetClassification(
                text_id, "text", ROLE_BEAM_IDENTIFIER, 0.98, CLASSIFICATION_SOURCE_TEXT
            )
        if layer == "SEC TEXT" and BEAM_LABEL_RE.match(raw):
            return SemanticAssetClassification(
                text_id,
                "text",
                ROLE_SECTION_IDENTIFIER,
                0.88,
                CLASSIFICATION_SOURCE_TEXT,
            )
        if NUMERIC_DIMENSION_RE.match(raw):
            return SemanticAssetClassification(
                text_id, "text", ROLE_DIMENSION, 0.92, CLASSIFICATION_SOURCE_TEXT
            )
        if TRANSVERSE_BAR_RE.search(upper):
            return SemanticAssetClassification(
                text_id, "text", ROLE_TRANSVERSE, 0.93, CLASSIFICATION_SOURCE_TEXT
            )
        if LONGITUDINAL_BAR_RE.match(raw):
            return SemanticAssetClassification(
                text_id, "text", ROLE_LONGITUDINAL, 0.94, CLASSIFICATION_SOURCE_TEXT
            )
        if upper.startswith("NOTE") or "DETAIL" in upper or "REFER" in upper:
            return SemanticAssetClassification(
                text_id, "text", ROLE_GENERAL_NOTE, 0.75, CLASSIFICATION_SOURCE_TEXT
            )
        if BEAM_LABEL_RE.search(raw):
            return SemanticAssetClassification(
                text_id, "text", ROLE_SECTION_IDENTIFIER, 0.8, CLASSIFICATION_SOURCE_TEXT
            )
        return SemanticAssetClassification(
            text_id, "text", ROLE_CALLOUT, 0.5, CLASSIFICATION_SOURCE_TEXT
        )

    def _link_leaders_to_text(
        self,
        leaders: Dict[str, dict[str, Any]],
        texts: Dict[str, dict[str, Any]],
    ) -> Dict[str, str]:
        links: Dict[str, str] = {}
        for leader_id, leader in leaders.items():
            end = leader.get("end", {})
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

    def _aggregate(
        self,
        asset_classes: List[SemanticAssetClassification],
        assigned: Dict[str, str],
        leader_to_text: Dict[str, str],
    ) -> List[SemanticRoleBucket]:
        by_type: Dict[str, SemanticRoleBucket] = {}
        confidences: Dict[str, List[float]] = {}
        sources: Dict[str, set[str]] = {}

        def add(role_type: str, kind: str, asset_id: str, confidence: float, source: str) -> None:
            if role_type not in VALID_SEMANTIC_ROLE_TYPES:
                role_type = ROLE_UNKNOWN
            bucket = by_type.setdefault(role_type, SemanticRoleBucket(role_type=role_type))
            key = {"geometry": "geometry", "text": "text", "leader": "leaders", "block": "blocks"}[
                kind
            ]
            if asset_id not in getattr(bucket, key):
                getattr(bucket, key).append(asset_id)
            confidences.setdefault(role_type, []).append(confidence)
            sources.setdefault(role_type, set()).add(source)

        for cls in asset_classes:
            add(cls.role_type, cls.asset_kind, cls.asset_id, cls.confidence, cls.classification_source)

        buckets: List[SemanticRoleBucket] = []
        singleton_types = {
            ROLE_BEAM_IDENTIFIER,
            ROLE_DEVELOPMENT_LENGTH,
            ROLE_DIMENSION,
            ROLE_SIDE_FACE,
            ROLE_SPACER,
            ROLE_HOOK,
            ROLE_ANCHORAGE,
        }

        for role_type, bucket in by_type.items():
            if role_type in singleton_types and bucket.text:
                for text_id in bucket.text:
                    buckets.append(
                        SemanticRoleBucket(
                            role_type=role_type,
                            text=[text_id],
                            leaders=[
                                lid
                                for lid, tid in leader_to_text.items()
                                if tid == text_id
                            ],
                            confidence=0.9,
                            classification_source=CLASSIFICATION_SOURCE_TEXT,
                        )
                    )
                geom = list(bucket.geometry)
                if geom:
                    buckets.append(
                        SemanticRoleBucket(
                            role_type=role_type,
                            geometry=geom,
                            confidence=0.85,
                            classification_source=CLASSIFICATION_SOURCE_GEOMETRY,
                        )
                    )
                continue

            avg_conf = sum(confidences.get(role_type, [0.5])) / max(
                len(confidences.get(role_type, [0.5])), 1
            )
            srcs = sources.get(role_type, {CLASSIFICATION_SOURCE_GEOMETRY})
            source = (
                CLASSIFICATION_SOURCE_GEOMETRY_AND_TEXT
                if len(srcs) > 1
                else next(iter(srcs))
            )
            buckets.append(
                SemanticRoleBucket(
                    role_type=role_type,
                    geometry=list(bucket.geometry),
                    text=list(bucket.text),
                    leaders=list(bucket.leaders),
                    blocks=list(bucket.blocks),
                    confidence=round(avg_conf, 2),
                    classification_source=source,
                )
            )

        if not buckets:
            buckets.append(SemanticRoleBucket(role_type=ROLE_UNKNOWN))

        return buckets
