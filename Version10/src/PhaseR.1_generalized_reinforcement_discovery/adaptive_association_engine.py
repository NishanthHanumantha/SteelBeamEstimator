"""
adaptive_association_engine.py — Phase R.1.1A multi-evidence beam-detail association.
MODEL_VERSION: 9.2.0

Replaces fixed-radius nearest-centroid assignment with:
  • adaptive per-beam search regions
  • detail cluster reconstruction (beam-mark anchoring)
  • leader-driven association (DXF + optional R.3.1)
  • multi-evidence scoring
  • orphan annotation recovery

9.2.0: optionally collect DIMENSION text overrides (discovery.enable_dimension_text_scan).
"""
from __future__ import annotations

import json
import logging
import math
import pathlib
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .dxf_text_utils import (
    entity_position,
    entity_raw_text,
    is_dimension_entity,
    strip_mtext as _strip_mtext,
)
from .reinforcement_models import BeamDetail

log = logging.getLogger(__name__)

_BEAM_MARK_RE = re.compile(r"^(B\d+[A-Z]?)\b", re.I)
_RE_BAR_HINT = re.compile(r"[YyRrTt]\s*\d+|@\s*\d", re.I)

ASSOC_NEAREST = "nearest_beam"
ASSOC_LEADER = "leader"
ASSOC_CLUSTER = "cluster"
ASSOC_HYBRID = "hybrid"
ASSOC_ORPHAN_RECOVERY = "orphan_recovery"
ASSOC_PROJECTION = "projection"


@dataclass
class SearchRegion:
    beam_id: str
    center_x: float
    center_y: float
    radius: float
    span_mm: float
    depth_mm: float
    width_mm: float
    anchor_sources: List[str] = field(default_factory=list)


@dataclass
class DetailCluster:
    cluster_id: str
    beam_id: str
    center_x: float
    center_y: float
    member_count: int = 0
    has_beam_mark: bool = False
    leader_count: int = 0


@dataclass
class LeaderRecord:
    leader_id: str
    beam_id: str
    tip_x: float
    tip_y: float
    tail_x: float
    tail_y: float
    source: str = "dxf"


class AdaptiveAssociationEngine:
    """Multi-evidence annotation-to-beam association engine."""

    def __init__(self, config: dict, project_root: pathlib.Path):
        geo = config.get("geometry", {})
        r11a = config.get("r11a", {})
        disc = config.get("discovery", {})
        self._min_radius = float(r11a.get("min_search_radius", geo.get("min_search_radius", 8000.0)))
        self._max_radius = float(r11a.get("max_search_radius", geo.get("max_search_radius", 25000.0)))
        self._legacy_radius = float(geo.get("annotation_search_radius", 5000.0))
        self._leader_tail_tol = float(r11a.get("leader_tail_tolerance", 500.0))
        self._score_threshold = float(r11a.get("association_score_threshold", 0.25))
        self._orphan_expand = float(r11a.get("orphan_radius_multiplier", 1.35))
        # Widen discovery to DIMENSION text overrides (Set 1–3 stirrup channel).
        # Flag false → pre-9.2.0 TEXT/MTEXT-only behavior.
        self._enable_dimension_text_scan = bool(
            disc.get("enable_dimension_text_scan", False)
        )
        self._project_root = project_root
        self._registry: Dict[str, Any] = {}

        self.search_regions: List[SearchRegion] = []
        self.clusters: List[DetailCluster] = []
        self.association_scores: List[Dict[str, Any]] = []
        self.orphan_recoveries: List[Dict[str, Any]] = []
        self._leaders: List[LeaderRecord] = []
        self._r31_by_tail: Dict[Tuple[float, float], str] = {}

    def segment(
        self,
        msp,
        details: List[BeamDetail],
        registry: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[dict]]:
        self._registry = registry or {}
        self._load_r31_leaders()
        self._discover_dxf_leaders(msp, details)

        entities = self._collect_entities(msp)
        self._build_search_regions(details, entities)
        self._build_detail_clusters(details, entities)

        beam_map: Dict[str, List[dict]] = {d.beam_id: [] for d in details}
        assigned_keys: set = set()

        for idx, ent in enumerate(entities):
            best = self._score_entity(ent, details, pass_name="primary")
            if best and best["total_score"] >= self._score_threshold:
                bid = best["beam_id"]
                rec = self._make_record(ent, best)
                beam_map[bid].append(rec)
                assigned_keys.add(idx)
                self.association_scores.append(best)

        orphans = [entities[i] for i in range(len(entities)) if i not in assigned_keys]
        for ent in orphans:
            best = self._score_entity(ent, details, pass_name="orphan", radius_mult=self._orphan_expand)
            if best and best["total_score"] >= self._score_threshold * 0.85:
                bid = best["beam_id"]
                best["association_method"] = ASSOC_ORPHAN_RECOVERY
                rec = self._make_record(ent, best)
                beam_map[bid].append(rec)
                self.orphan_recoveries.append(
                    {
                        "x": ent["x"],
                        "y": ent["y"],
                        "clean_text": ent["clean_text"][:80],
                        "beam_id": bid,
                        "score": best["total_score"],
                        "method": ASSOC_ORPHAN_RECOVERY,
                    }
                )
                self.association_scores.append(best)
            else:
                self.orphan_recoveries.append(
                    {
                        "x": ent["x"],
                        "y": ent["y"],
                        "clean_text": ent["clean_text"][:80],
                        "beam_id": None,
                        "score": best["total_score"] if best else 0.0,
                        "method": "unrecovered",
                        "reason": "No beam exceeded engineering score threshold",
                    }
                )

        for d in details:
            d.entity_count = len(beam_map.get(d.beam_id, []))
            sr = next((r for r in self.search_regions if r.beam_id == d.beam_id), None)
            if sr:
                d.detail_radius = sr.radius

        total = sum(len(v) for v in beam_map.values())
        log.info(
            "AdaptiveAssociationEngine: %d entities assigned, %d orphan recoveries, %d unrecovered",
            total,
            sum(1 for o in self.orphan_recoveries if o.get("beam_id")),
            sum(1 for o in self.orphan_recoveries if not o.get("beam_id")),
        )
        return beam_map

    def _entity_allowed(self, entity) -> bool:
        dtype = entity.dxftype()
        if dtype in ("TEXT", "MTEXT"):
            return True
        if self._enable_dimension_text_scan and is_dimension_entity(entity):
            return True
        return False

    def _collect_entities(self, msp) -> List[dict]:
        """Collect annotation-bearing entities from modelspace.

        TEXT/MTEXT always. DIMENSION text overrides when
        discovery.enable_dimension_text_scan is true. Same record shape
        for all sources so downstream classification is unchanged.
        Nesting/INSERT handling matches existing TEXT/MTEXT traversal
        (modelspace iteration only — no parallel DIMENSION path).
        """
        out: List[dict] = []
        n_dim = 0
        for entity in msp:
            if not self._entity_allowed(entity):
                continue
            pos = entity_position(entity)
            if pos is None:
                continue
            x, y = pos
            raw = entity_raw_text(entity)
            clean = _strip_mtext(raw)
            if not clean:
                continue
            et = entity.dxftype()
            if is_dimension_entity(entity):
                n_dim += 1
            out.append(
                {
                    "x": x,
                    "y": y,
                    "raw_text": raw,
                    "clean_text": clean,
                    "entity_type": et,
                }
            )
        if self._enable_dimension_text_scan:
            log.info(
                "AdaptiveAssociationEngine: collected %d entities "
                "(%d DIMENSION text overrides)",
                len(out),
                n_dim,
            )
        return out

    def _compute_adaptive_radius(self, beam_id: str, detail: BeamDetail) -> float:
        rec = self._registry.get(beam_id, {})
        span = float(rec.get("clear_span_mm") or detail.section.get("clear_span_mm") or 8000.0)
        depth = float(detail.section.get("depth_mm") or 750.0)
        width = float(detail.section.get("width_mm") or 400.0)
        radius = max(span * 0.55, depth * 10.0, width * 12.0, self._min_radius)
        return min(radius, self._max_radius)

    def _find_beam_mark_anchor(
        self, beam_id: str, entities: List[dict]
    ) -> Optional[Tuple[float, float]]:
        mark = beam_id.upper()
        for ent in entities:
            cs = ent["clean_text"].strip().upper()
            m = _BEAM_MARK_RE.match(cs)
            if m and m.group(1).upper() == mark:
                return (ent["x"], ent["y"])
        return None

    def _build_search_regions(self, details: List[BeamDetail], entities: List[dict]) -> None:
        self.search_regions = []
        for detail in details:
            rec = self._registry.get(detail.beam_id, {})
            span = float(rec.get("clear_span_mm") or 8000.0)
            depth = float(detail.section.get("depth_mm") or 750.0)
            width = float(detail.section.get("width_mm") or 400.0)
            radius = self._compute_adaptive_radius(detail.beam_id, detail)

            anchors = [(detail.centroid_x, detail.centroid_y, "registry_centroid")]
            mark = self._find_beam_mark_anchor(detail.beam_id, entities)
            if mark:
                anchors.append((mark[0], mark[1], "beam_mark_text"))

            leader_pts = [
                (lr.tail_x, lr.tail_y, "leader_tail")
                for lr in self._leaders
                if lr.beam_id == detail.beam_id
            ]
            for lx, ly, src in leader_pts[:5]:
                anchors.append((lx, ly, src))

            cx = sum(a[0] for a in anchors) / len(anchors)
            cy = sum(a[1] for a in anchors) / len(anchors)

            self.search_regions.append(
                SearchRegion(
                    beam_id=detail.beam_id,
                    center_x=round(cx, 2),
                    center_y=round(cy, 2),
                    radius=round(radius, 2),
                    span_mm=span,
                    depth_mm=depth,
                    width_mm=width,
                    anchor_sources=[a[2] for a in anchors],
                )
            )

    def _build_detail_clusters(self, details: List[BeamDetail], entities: List[dict]) -> None:
        self.clusters = []
        region_map = {r.beam_id: r for r in self.search_regions}
        for detail in details:
            region = region_map.get(detail.beam_id)
            if not region:
                continue
            members = [
                e for e in entities
                if self._dist(e["x"], e["y"], region.center_x, region.center_y) <= region.radius
            ]
            has_mark = any(
                _BEAM_MARK_RE.match(e["clean_text"].strip().upper())
                and _BEAM_MARK_RE.match(e["clean_text"].strip().upper()).group(1).upper() == detail.beam_id
                for e in members
            )
            lc = sum(1 for lr in self._leaders if lr.beam_id == detail.beam_id)
            self.clusters.append(
                DetailCluster(
                    cluster_id=f"CLU-{detail.beam_id}-{uuid.uuid4().hex[:6]}",
                    beam_id=detail.beam_id,
                    center_x=region.center_x,
                    center_y=region.center_y,
                    member_count=len(members),
                    has_beam_mark=has_mark,
                    leader_count=lc,
                )
            )

    def _load_r31_leaders(self) -> None:
        p = (
            self._project_root
            / "data/output/PhaseR3.1_engineering_relationship_engine"
            / "EngineeringDrawingRelationships.json"
        )
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            for rel in data.get("relationships", []):
                aid = rel.get("annotation_id")
                bid = rel.get("beam_id")
                if aid and bid:
                    self._r31_by_tail[(rel.get("leader_id", aid))] = bid
        except Exception as exc:
            log.warning("Could not load R.3.1 relationships: %s", exc)

    def _discover_dxf_leaders(self, msp, details: List[BeamDetail]) -> None:
        detail_map = {d.beam_id: d for d in details}
        for entity in msp:
            if entity.dxftype() != "LEADER":
                continue
            try:
                verts = [(float(v[0]), float(v[1])) for v in entity.vertices]
            except Exception:
                continue
            if len(verts) < 2:
                continue
            tip, tail = verts[0], verts[-1]
            bid = self._assign_leader_beam(tip, tail, details)
            self._leaders.append(
                LeaderRecord(
                    leader_id=f"LDR-{uuid.uuid4().hex[:8]}",
                    beam_id=bid,
                    tip_x=tip[0],
                    tip_y=tip[1],
                    tail_x=tail[0],
                    tail_y=tail[1],
                    source="dxf",
                )
            )

    def _assign_leader_beam(
        self, tip: Tuple[float, float], tail: Tuple[float, float], details: List[BeamDetail]
    ) -> str:
        mid = ((tip[0] + tail[0]) / 2, (tip[1] + tail[1]) / 2)
        best_id = details[0].beam_id if details else ""
        best_d = float("inf")
        for d in details:
            dist = self._dist(mid[0], mid[1], d.centroid_x, d.centroid_y)
            if dist < best_d:
                best_d = dist
                best_id = d.beam_id
        return best_id

    def _score_entity(
        self,
        ent: dict,
        details: List[BeamDetail],
        pass_name: str = "primary",
        radius_mult: float = 1.0,
    ) -> Optional[Dict[str, Any]]:
        x, y = ent["x"], ent["y"]
        best: Optional[Dict[str, Any]] = None

        for region in self.search_regions:
            eff_radius = region.radius * radius_mult
            dist = self._dist(x, y, region.center_x, region.center_y)
            if dist > eff_radius:
                continue

            distance_score = max(0.0, 1.0 - dist / eff_radius)
            leader_score = self._leader_score(x, y, region.beam_id)
            cluster_score = 1.0 if dist <= region.radius * 0.65 else 0.5
            bar_hint_score = 0.15 if _RE_BAR_HINT.search(ent["clean_text"]) else 0.0
            mark_score = 0.0
            cs = ent["clean_text"].strip().upper()
            m = _BEAM_MARK_RE.match(cs)
            if m and m.group(1).upper() == region.beam_id:
                mark_score = 0.2

            total = (
                distance_score * 0.35
                + leader_score * 0.30
                + cluster_score * 0.20
                + bar_hint_score
                + mark_score
            )
            if leader_score >= 0.9:
                method = ASSOC_LEADER
            elif mark_score > 0:
                method = ASSOC_CLUSTER
            elif leader_score > 0.3:
                method = ASSOC_HYBRID
            else:
                method = ASSOC_NEAREST

            row = {
                "beam_id": region.beam_id,
                "x": x,
                "y": y,
                "clean_text": ent["clean_text"][:80],
                "pass": pass_name,
                "distance": round(dist, 2),
                "effective_radius": round(eff_radius, 2),
                "distance_score": round(distance_score, 4),
                "leader_score": round(leader_score, 4),
                "cluster_score": round(cluster_score, 4),
                "bar_hint_score": round(bar_hint_score, 4),
                "total_score": round(total, 4),
                "association_method": method,
                "evidence": [
                    f"distance={dist:.0f}/{eff_radius:.0f}",
                    f"leader={leader_score:.2f}",
                    f"cluster={cluster_score:.2f}",
                ],
                "association_confidence": round(min(1.0, total), 4),
            }
            if best is None or row["total_score"] > best["total_score"]:
                best = row
        return best

    def _leader_score(self, x: float, y: float, beam_id: str) -> float:
        best = 0.0
        for lr in self._leaders:
            if lr.beam_id != beam_id:
                continue
            d_tail = self._dist(x, y, lr.tail_x, lr.tail_y)
            d_tip = self._dist(x, y, lr.tip_x, lr.tip_y)
            d = min(d_tail, d_tip)
            if d <= self._leader_tail_tol:
                best = max(best, 1.0 - d / self._leader_tail_tol)
        return best

    @staticmethod
    def _dist(x1: float, y1: float, x2: float, y2: float) -> float:
        return math.hypot(x1 - x2, y1 - y2)

    @staticmethod
    def _make_record(ent: dict, score_row: Dict[str, Any]) -> dict:
        return {
            "x": ent["x"],
            "y": ent["y"],
            "raw_text": ent["raw_text"],
            "clean_text": ent["clean_text"],
            "entity_type": ent["entity_type"],
            "distance": score_row["distance"],
            "association_score": score_row["total_score"],
            "association_method": score_row["association_method"],
            "association_confidence": score_row["association_confidence"],
            "association_evidence": score_row["evidence"],
        }
