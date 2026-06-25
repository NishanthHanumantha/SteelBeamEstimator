"""Phase D.3.3 — reconcile engineering annotation ownership from geometry."""

import re
from typing import Any, Dict, List, Set, Tuple

from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key
from src.ownership.annotation_conflict_resolver import AnnotationConflictResolver
from src.ownership.annotation_region_matcher import AnnotationRegionMatcher
from src.ownership.annotation_sketch_matcher import AnnotationSketchMatcher
from src.ownership.leader_geometry_matcher import LeaderGeometryMatcher
from src.ownership.ownership_geometry import find_cell_for_point
from src.ownership.ownership_types import coord_key, flatten_engineering_records

_SHARED_KEYWORDS = (
    "SIDE FACE",
    "SFR",
    "S F R",
    "FACE REINF",
    "ON BOTH FACE",
    "ON BOTH FACES",
    "TYPICAL",
)


class OwnershipReconciliationEngine:
    """Recompute annotation ownership from geometry — ignore historical beam_mark."""

    def reconcile(
        self,
        engineering_records: List[dict[str, Any]],
        detail_regions: List[dict[str, Any]],
        beam_groups: List[dict[str, Any]],
        beam_cells: List[dict[str, Any]],
        dxf_path: str | None = None,
    ) -> Dict[str, Any]:
        flat = flatten_engineering_records(engineering_records)
        cell_by_mark = {str(c["beam_mark"]).upper(): c for c in beam_cells}
        region_by_id = {r["region_id"]: r for r in detail_regions}
        group_by_region = {
            g.get("detail_region_id", ""): g for g in beam_groups
        }

        leader_matcher = LeaderGeometryMatcher(dxf_path)
        region_matcher = AnnotationRegionMatcher(detail_regions)
        sketch_matcher = AnnotationSketchMatcher(cell_by_mark)
        resolver = AnnotationConflictResolver(region_matcher, sketch_matcher)

        master: List[dict[str, Any]] = []
        region_mapping: List[dict[str, Any]] = []
        sketch_mapping: List[dict[str, Any]] = []
        conflicts: List[dict[str, Any]] = []
        confidence_records: List[dict[str, Any]] = []

        for ann in flat:
            insert_x = float(ann["x"])
            insert_y = float(ann["y"])
            eval_x, eval_y, has_leader, leader_pt = leader_matcher.resolve(
                insert_x, insert_y
            )
            cell = find_cell_for_point(insert_x, insert_y, beam_cells)
            cell_mark = (
                str(cell["beam_mark"]).upper() if cell is not None else None
            )

            ownership, candidates = resolver.resolve(
                insert_x,
                insert_y,
                eval_x,
                eval_y,
                has_leader,
                cell_mark,
            )

            if cell_mark:
                enforced = self._enforce_cell_primary(
                    cell_mark,
                    insert_x,
                    insert_y,
                    detail_regions,
                    has_leader,
                    eval_x,
                    eval_y,
                )
                if enforced is not None:
                    ownership = enforced

            if ownership["ownership_status"] == "UNASSIGNED" and cell_mark:
                ownership = self._cell_fallback(
                    ownership,
                    cell_mark,
                    detail_regions,
                    insert_x,
                    insert_y,
                )

            record = self._build_master_record(ann, ownership, leader_pt, candidates)
            master.append(record)

            if ownership.get("is_ambiguous") and len(candidates) > 1:
                conflicts.append(
                    {
                        "annotation_id": ann["annotation_id"],
                        "clean_text": ann.get("clean_text", ""),
                        "candidates": [
                            {
                                "region_id": c["region_id"],
                                "score": c["total_score"],
                                "sketch_id": c["sketch"]["sketch_id"],
                                "beam_mark": c["sketch"]["beam_mark"],
                            }
                            for c in candidates[:3]
                        ],
                    }
                )

            if ownership["detail_region_id"]:
                region_mapping.append(
                    {
                        "annotation_id": ann["annotation_id"],
                        "detail_region_id": ownership["detail_region_id"],
                        "beam_titles": region_by_id[
                            ownership["detail_region_id"]
                        ]["beam_titles"],
                    }
                )
            if ownership.get("resolved_sketch_id"):
                sketch_mapping.append(
                    {
                        "annotation_id": ann["annotation_id"],
                        "sketch_id": ownership["resolved_sketch_id"],
                        "beam_mark": ownership["resolved_beam_mark"],
                    }
                )
            confidence_records.append(
                {
                    "annotation_id": ann["annotation_id"],
                    "confidence_score": ownership["confidence_score"],
                    "confidence_label": ownership["confidence_label"],
                    "ownership_status": ownership["ownership_status"],
                }
            )

        master = self._apply_region_expansion(
            master, detail_regions, group_by_region, flat
        )

        logger.info(
            "Reconciled {} annotation(s) — {} owned, {} ambiguous, {} unassigned",
            len(master),
            sum(1 for m in master if m["ownership_status"] == "OWNED"),
            sum(1 for m in master if m["ownership_status"] == "AMBIGUOUS"),
            sum(1 for m in master if m["ownership_status"] == "UNASSIGNED"),
        )

        return {
            "master": master,
            "region_mapping": region_mapping,
            "sketch_mapping": sketch_mapping,
            "confidence": confidence_records,
            "conflicts": conflicts,
        }

    def _build_master_record(
        self,
        ann: dict[str, Any],
        ownership: dict[str, Any],
        leader_pt: Tuple[float, float] | None,
        candidates: List[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "annotation_id": ann["annotation_id"],
            "clean_text": ann.get("clean_text", ""),
            "annotation_type": ann.get("annotation_type", ""),
            "entity_type": ann.get("entity_type", ""),
            "x": float(ann["x"]),
            "y": float(ann["y"]),
            "eval_x": ownership["eval_x"],
            "eval_y": ownership["eval_y"],
            "leader_endpoint": (
                {"x": leader_pt[0], "y": leader_pt[1]} if leader_pt else None
            ),
            "historical_beam_mark": ann.get("historical_beam_mark"),
            "historical_sketch_id": ann.get("historical_sketch_id"),
            "ownership_status": ownership["ownership_status"],
            "detail_region_id": ownership.get("detail_region_id"),
            "resolved_beam_mark": ownership.get("resolved_beam_mark"),
            "resolved_sketch_id": ownership.get("resolved_sketch_id"),
            "confidence_score": ownership["confidence_score"],
            "confidence_label": ownership["confidence_label"],
            "component_scores": ownership["component_scores"],
            "has_leader": ownership["has_leader"],
            "is_ambiguous": ownership.get("is_ambiguous", False),
            "expanded_beams": [],
            "expanded_from_region": False,
            "engineering_source": ann.get("engineering_source", ""),
            "final_status": ann.get("final_status", ""),
            "candidate_count": len(candidates),
        }

    def _apply_region_expansion(
        self,
        master: List[dict[str, Any]],
        detail_regions: List[dict[str, Any]],
        group_by_region: Dict[str, dict[str, Any]],
        flat: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        """Expand shared annotations only within the owned detail region."""
        region_titles = {
            r["region_id"]: set(r["beam_titles"]) for r in detail_regions
        }
        duplicate_map = self._duplicate_beam_map(flat)

        for record in master:
            if record["ownership_status"] != "OWNED":
                continue
            region_id = record.get("detail_region_id")
            if not region_id:
                continue
            titles = region_titles.get(region_id, set())
            if len(titles) < 2:
                record["expanded_beams"] = sorted(
                    {record["resolved_beam_mark"]},
                    key=beam_mark_sort_key,
                )
                continue

            clean = str(record.get("clean_text", ""))
            x, y = float(record["x"]), float(record["y"])
            dup_beams = {
                m
                for m in duplicate_map.get(coord_key(clean, x, y), [])
                if m in titles
            }
            expand = False
            if len(dup_beams) >= 2:
                expand = True
            if self._looks_shared(clean) and len(titles) >= 2:
                expand = True

            if expand:
                record["expanded_beams"] = sorted(titles, key=beam_mark_sort_key)
                record["expanded_from_region"] = True
                group = group_by_region.get(region_id)
                if group:
                    record["beam_group_id"] = group.get("beam_group_id")
            else:
                record["expanded_beams"] = sorted(
                    {record["resolved_beam_mark"]},
                    key=beam_mark_sort_key,
                )
        return master

    def _duplicate_beam_map(
        self, annotations: List[dict[str, Any]]
    ) -> Dict[Tuple[str, float, float], List[str]]:
        buckets: Dict[Tuple[str, float, float], List[str]] = {}
        for ann in annotations:
            key = coord_key(
                str(ann.get("clean_text", "")),
                float(ann["x"]),
                float(ann["y"]),
            )
            mark = str(ann.get("historical_beam_mark", "")).upper()
            buckets.setdefault(key, [])
            if mark and mark not in buckets[key]:
                buckets[key].append(mark)
        return buckets

    def _looks_shared(self, clean_text: str) -> bool:
        upper = clean_text.upper()
        return any(kw in upper for kw in _SHARED_KEYWORDS)

    def _enforce_cell_primary(
        self,
        cell_mark: str,
        insert_x: float,
        insert_y: float,
        detail_regions: List[dict[str, Any]],
        has_leader: bool,
        eval_x: float,
        eval_y: float,
    ) -> dict[str, Any] | None:
        """Force ownership to the beam cell column (overrides overlapping sketch geometry)."""
        candidates = [
            r
            for r in detail_regions
            if cell_mark in {str(t).upper() for t in r.get("beam_titles", [])}
        ]
        if not candidates:
            return None

        region = min(
            candidates,
            key=lambda r: self._min_sketch_dist_for_mark(
                r, cell_mark, eval_x, eval_y
            ),
        )
        dist = self._min_sketch_dist_for_mark(region, cell_mark, eval_x, eval_y)
        if dist > 12000.0:
            return None

        sketch = self._nearest_sketch_for_mark(
            region, cell_mark, eval_x, eval_y
        )
        if sketch is None:
            return None

        score = 70.0 if dist < 2000.0 else 55.0
        if has_leader:
            score = min(90.0, score + 10.0)
        label = "HIGH" if score >= 85 else "MEDIUM" if score >= 60 else "LOW"

        return {
            "ownership_status": "OWNED",
            "detail_region_id": region["region_id"],
            "resolved_beam_mark": cell_mark,
            "resolved_sketch_id": str(sketch["sketch_id"]),
            "eval_x": eval_x,
            "eval_y": eval_y,
            "insert_x": insert_x,
            "insert_y": insert_y,
            "has_leader": has_leader,
            "is_ambiguous": False,
            "confidence_score": int(round(score)),
            "confidence_label": label,
            "component_scores": {
                "leader": 10.0 if has_leader else 0.0,
                "sketch_overlap": 15.0,
                "region_containment": 15.0,
                "reinforcement_geometry": 15.0,
                "distance": 5.0,
                "orientation": 5.0,
            },
        }

    def _min_sketch_dist_for_mark(
        self,
        region: dict[str, Any],
        mark: str,
        x: float,
        y: float,
    ) -> float:
        from src.utils.bbox_utils import distance_point_to_bbox

        sketches = [
            s
            for s in region.get("member_sketches", [])
            if str(s["beam_mark"]).upper() == mark.upper()
        ]
        if not sketches:
            return float("inf")
        return min(distance_point_to_bbox(x, y, s["bbox"]) for s in sketches)

    def _cell_fallback(
        self,
        ownership: dict[str, Any],
        cell_mark: str,
        detail_regions: List[dict[str, Any]],
        insert_x: float,
        insert_y: float,
    ) -> dict[str, Any]:
        """Assign to region containing the beam cell when geometry score is weak."""
        candidates = [
            r
            for r in detail_regions
            if cell_mark in {str(t).upper() for t in r.get("beam_titles", [])}
        ]
        if not candidates:
            return ownership

        region = min(
            candidates,
            key=lambda r: self._min_sketch_dist(r, insert_x, insert_y),
        )
        sketch = self._nearest_sketch_for_mark(region, cell_mark, insert_x, insert_y)
        if sketch is None:
            return ownership

        dist = self._min_sketch_dist(region, insert_x, insert_y)
        if dist > 15000.0:
            return ownership

        ownership = dict(ownership)
        ownership["ownership_status"] = "OWNED"
        ownership["detail_region_id"] = region["region_id"]
        ownership["resolved_beam_mark"] = cell_mark
        ownership["resolved_sketch_id"] = str(sketch["sketch_id"])
        ownership["confidence_score"] = max(45, ownership.get("confidence_score", 0))
        ownership["confidence_label"] = "MEDIUM"
        ownership["is_ambiguous"] = False
        return ownership

    def _nearest_sketch_for_mark(
        self,
        region: dict[str, Any],
        mark: str,
        x: float,
        y: float,
    ) -> dict[str, Any] | None:
        sketches = [
            s
            for s in region.get("member_sketches", [])
            if str(s["beam_mark"]).upper() == mark.upper()
        ]
        if not sketches:
            return None
        from src.utils.bbox_utils import distance_point_to_bbox

        return min(
            sketches,
            key=lambda s: distance_point_to_bbox(x, y, s["bbox"]),
        )

    def _min_sketch_dist(
        self, region: dict[str, Any], x: float, y: float
    ) -> float:
        from src.utils.bbox_utils import distance_point_to_bbox

        sketches = region.get("member_sketches", [])
        if not sketches:
            return float("inf")
        return min(
            distance_point_to_bbox(x, y, s["bbox"]) for s in sketches
        )
