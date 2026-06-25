"""Phase D.3.1 — multi-rule confidence scoring for detected beam groups."""

import math
from typing import Any, Dict, List, Optional, Tuple

from src.framing.beam_geometry import beam_mark_sort_key
from src.grouping.beam_group_types import BeamGroup
from src.utils.bbox_utils import (
    bbox_height,
    bbox_width,
    horizontal_overlap_ratio,
    sketches_for_beam,
    union_bbox,
    vertical_band_overlap_ratio,
)

SKETCH_LINK_GAP_TOLERANCE_MM = 2000.0
SKETCH_LINK_MIN_VERTICAL_OVERLAP = 0.30
CELL_ADJACENCY_TOLERANCE_MM = 5.0
TITLE_INSIDE_DETAIL_MARGIN_MM = 1500.0

WEIGHTS: Dict[str, float] = {
    "sketch_span": 25.0,
    "shared_annotations": 20.0,
    "title_pattern": 15.0,
    "geometry_similarity": 15.0,
    "adjacency": 10.0,
    "alignment": 10.0,
    "beam_count": 5.0,
}


class BeamGroupConfidenceScorer:
    """Score beam groups using independent engineering signals (read-only)."""

    def score_all(
        self,
        beam_groups: List[BeamGroup],
        sketches: List[dict[str, Any]],
        header_occurrences: List[dict[str, Any]],
        shared_annotations: List[dict[str, Any]],
        expanded_annotations: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        header_index = self._index_headers(header_occurrences)
        results: List[dict[str, Any]] = []

        for group in beam_groups:
            results.append(
                self._score_group(
                    group,
                    sketches,
                    header_index,
                    shared_annotations,
                    expanded_annotations,
                )
            )
        return results

    def _score_group(
        self,
        group: BeamGroup,
        sketches: List[dict[str, Any]],
        header_index: Dict[str, Tuple[float, float]],
        shared_annotations: List[dict[str, Any]],
        expanded_annotations: List[dict[str, Any]],
    ) -> dict[str, Any]:
        members = sorted(group["members"], key=beam_mark_sort_key)
        member_sketches = [
            sk
            for mark in members
            for sk in sketches_for_beam(mark, sketches)
        ]
        clusters = self._sketch_clusters(member_sketches)
        detail_cluster_count = len(clusters)

        rule_scores = {
            "beam_count": self._score_beam_count(group, detail_cluster_count),
            "sketch_span": self._score_sketch_span(group, member_sketches, clusters),
            "adjacency": self._score_adjacency(group),
            "shared_annotations": self._score_shared_annotations(
                group, shared_annotations, expanded_annotations
            ),
            "title_pattern": self._score_title_pattern(group, header_index),
            "alignment": self._score_alignment(group),
            "geometry_similarity": self._score_geometry_similarity(group, sketches),
        }

        weighted = sum(
            rule_scores[key] * (WEIGHTS[key] / 100.0) for key in WEIGHTS
        )
        confidence_score = int(round(max(0.0, min(100.0, weighted))))

        if (
            group["is_multi_beam"]
            and detail_cluster_count >= len(members)
            and rule_scores["sketch_span"] < 55.0
        ):
            confidence_score = min(confidence_score, 59)
        confidence = self._confidence_label(confidence_score)

        warnings = self._build_warnings(group, rule_scores, detail_cluster_count)
        if group["is_multi_beam"] and confidence_score < 60:
            warnings.append("INVALID_GROUP: multi-beam group below confidence threshold")

        reasons = self._build_reasons(group, rule_scores, detail_cluster_count)

        return {
            "group_id": group["beam_group_id"],
            "members": members,
            "is_multi_beam": group["is_multi_beam"],
            "confidence_score": confidence_score,
            "confidence": confidence,
            "rule_scores": {k: int(round(v)) for k, v in rule_scores.items()},
            "detail_sketch_cluster_count": detail_cluster_count,
            "warnings": warnings,
            "reasons": reasons,
            "recommendation": self._recommendation(group, confidence_score, rule_scores),
        }

    def _score_beam_count(
        self, group: BeamGroup, detail_cluster_count: int
    ) -> float:
        member_count = len(group["members"])
        if not group["is_multi_beam"]:
            return 100.0 if member_count == 1 else 40.0

        if member_count >= 2 and detail_cluster_count == 1:
            return 100.0
        if detail_cluster_count >= member_count:
            return 25.0
        return 70.0

    def _score_sketch_span(
        self,
        group: BeamGroup,
        member_sketches: List[dict[str, Any]],
        clusters: List[List[dict[str, Any]]],
    ) -> float:
        if not member_sketches:
            return 30.0

        member_count = len(group["members"])
        cluster_count = len(clusters)

        if not group["is_multi_beam"]:
            return 95.0 if cluster_count <= 3 else 70.0

        if cluster_count == 1:
            envelope = union_bbox([s["bbox"] for s in member_sketches])
            cell_union = group["bounding_box"]
            coverage = horizontal_overlap_ratio(envelope, cell_union)
            return min(100.0, 85.0 + coverage * 15.0)

        if cluster_count >= member_count:
            return max(15.0, 40.0 - (cluster_count - member_count) * 10.0)

        ratio = 1.0 - (cluster_count - 1) / max(1, member_count - 1)
        return 50.0 + ratio * 40.0

    def _score_adjacency(self, group: BeamGroup) -> float:
        if not group["is_multi_beam"]:
            return 100.0

        cells = sorted(
            group["member_details"],
            key=lambda m: float(m["cell_bbox"]["xmin"]),
        )
        max_gap = 0.0
        for idx in range(1, len(cells)):
            gap = float(cells[idx]["cell_bbox"]["xmin"]) - float(
                cells[idx - 1]["cell_bbox"]["xmax"]
            )
            max_gap = max(max_gap, gap)

        if max_gap <= CELL_ADJACENCY_TOLERANCE_MM:
            return 100.0
        if max_gap <= 500.0:
            return 80.0
        if max_gap <= 2000.0:
            return 50.0
        return 20.0

    def _score_shared_annotations(
        self,
        group: BeamGroup,
        shared_annotations: List[dict[str, Any]],
        expanded_annotations: List[dict[str, Any]],
    ) -> float:
        group_id = group["beam_group_id"]
        members = set(group["members"])

        group_mode = [
            a
            for a in shared_annotations
            if a.get("beam_group_id") == group_id and a.get("ownership_mode") == "GROUP"
        ]
        expanded = [
            e
            for e in expanded_annotations
            if e.get("beam_group_id") == group_id and e.get("expanded_from_group")
        ]

        if not group["is_multi_beam"]:
            return 90.0 if not group_mode else 85.0

        if not group_mode and not expanded:
            return 35.0

        unique_group_anns = len({a.get("annotation_id") for a in group_mode})
        expansion_ratio = len(expanded) / max(1, len(members) * unique_group_anns)

        independent_dupes = sum(
            1
            for a in shared_annotations
            if a.get("ownership_mode") == "SINGLE"
            and a.get("original_beam_mark") in members
            and a.get("beam_group_id") == group_id
        )

        if unique_group_anns >= 1 and expansion_ratio >= 0.8:
            base = 92.0
        elif unique_group_anns >= 1:
            base = 78.0
        else:
            base = 40.0

        penalty = min(30.0, independent_dupes * 5.0)
        return max(20.0, base - penalty)

    def _score_title_pattern(
        self,
        group: BeamGroup,
        header_index: Dict[str, Tuple[float, float]],
    ) -> float:
        inside = 0
        total = 0
        margin = TITLE_INSIDE_DETAIL_MARGIN_MM
        for member in group["member_details"]:
            mark = str(member["beam_mark"]).upper()
            header = header_index.get(mark)
            if header is None:
                continue
            total += 1
            hx, hy = header
            cell = member["cell_bbox"]
            detail = member["detail_band"]
            in_column = cell["xmin"] - margin <= hx <= cell["xmax"] + margin
            if in_column:
                inside += 1

        if total == 0:
            return 50.0
        ratio = inside / total
        if not group["is_multi_beam"]:
            return 70.0 + ratio * 30.0
        return ratio * 100.0

    def _score_alignment(self, group: BeamGroup) -> float:
        bands = [m["detail_band"] for m in group["member_details"]]
        if not bands:
            return 50.0

        ymin_values = [b["ymin"] for b in bands]
        ymax_values = [b["ymax"] for b in bands]
        ymin_spread = max(ymin_values) - min(ymin_values)
        ymax_spread = max(ymax_values) - min(ymax_values)
        y_spread = max(ymin_spread, ymax_spread)
        group_height = bbox_height(group["detail_band"]) or 1.0

        if not group["is_multi_beam"]:
            return 95.0

        if y_spread <= 200.0:
            return 100.0
        if y_spread <= 600.0:
            return 85.0
        if y_spread <= group_height * 0.3:
            return 70.0
        return max(20.0, 100.0 - (y_spread / group_height) * 50.0)

    def _score_geometry_similarity(
        self, group: BeamGroup, sketches: List[dict[str, Any]]
    ) -> float:
        if not group["is_multi_beam"]:
            return 95.0

        widths: List[float] = []
        heights: List[float] = []
        for member in group["member_details"]:
            band = member["detail_band"]
            widths.append(bbox_width(band))
            heights.append(bbox_height(band))

        if len(widths) < 2:
            return 60.0

        width_cv = self._coefficient_of_variation(widths)
        height_cv = self._coefficient_of_variation(heights)
        avg_cv = (width_cv + height_cv) / 2.0

        if avg_cv <= 0.25:
            return 100.0
        if avg_cv <= 0.45:
            return 80.0
        if avg_cv <= 0.7:
            return 55.0
        return 30.0

    def _sketch_clusters(
        self, sketches: List[dict[str, Any]]
    ) -> List[List[dict[str, Any]]]:
        if not sketches:
            return []
        clusters: List[List[dict[str, Any]]] = []
        for sketch in sketches:
            placed = False
            for cluster in clusters:
                if any(self._sketches_link(sketch, other) for other in cluster):
                    cluster.append(sketch)
                    placed = True
                    break
            if not placed:
                clusters.append([sketch])

        merged = True
        while merged:
            merged = False
            new_clusters: List[List[dict[str, Any]]] = []
            for cluster in clusters:
                attached = False
                for existing in new_clusters:
                    if any(
                        self._sketches_link(a, b)
                        for a in cluster
                        for b in existing
                    ):
                        existing.extend(cluster)
                        attached = True
                        merged = True
                        break
                if not attached:
                    new_clusters.append(cluster)
            clusters = new_clusters
        return clusters

    def _sketches_link(
        self, sketch_a: dict[str, Any], sketch_b: dict[str, Any]
    ) -> bool:
        bbox_a = sketch_a["bbox"]
        bbox_b = sketch_b["bbox"]
        if horizontal_overlap_ratio(bbox_a, bbox_b) > 0.01:
            return True
        if vertical_band_overlap_ratio(bbox_a, bbox_b) < SKETCH_LINK_MIN_VERTICAL_OVERLAP:
            return False
        gap_ab = bbox_b["xmin"] - bbox_a["xmax"]
        gap_ba = bbox_a["xmin"] - bbox_b["xmax"]
        return -50.0 <= gap_ab <= SKETCH_LINK_GAP_TOLERANCE_MM or -50.0 <= gap_ba <= SKETCH_LINK_GAP_TOLERANCE_MM

    def _coefficient_of_variation(self, values: List[float]) -> float:
        if not values:
            return 1.0
        mean = sum(values) / len(values)
        if mean <= 0.0:
            return 1.0
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return math.sqrt(variance) / mean

    def _index_headers(
        self, occurrences: List[dict[str, Any]]
    ) -> Dict[str, Tuple[float, float]]:
        index: Dict[str, Tuple[float, float]] = {}
        for occ in occurrences:
            mark = str(occ["beam_mark"]).upper()
            if mark not in index:
                index[mark] = (float(occ["x"]), float(occ["y"]))
        return index

    def _confidence_label(self, score: int) -> str:
        if score >= 85:
            return "HIGH"
        if score >= 60:
            return "MEDIUM"
        return "LOW"

    def _build_warnings(
        self,
        group: BeamGroup,
        rule_scores: Dict[str, float],
        detail_cluster_count: int,
    ) -> List[str]:
        warnings: List[str] = []
        if group["is_multi_beam"] and detail_cluster_count > 1:
            warnings.append(
                f"Multiple independent detail sketch clusters ({detail_cluster_count})"
            )
        if rule_scores["sketch_span"] < 50.0:
            warnings.append("Weak continuous sketch span across members")
        if rule_scores["shared_annotations"] < 50.0:
            warnings.append("Low shared engineering annotation evidence")
        if rule_scores["title_pattern"] < 50.0:
            warnings.append("Beam titles poorly aligned with detail region")
        if rule_scores["adjacency"] < 50.0:
            warnings.append("Member cells are not fully adjacent")
        return warnings

    def _build_reasons(
        self,
        group: BeamGroup,
        rule_scores: Dict[str, float],
        detail_cluster_count: int,
    ) -> List[str]:
        reasons: List[str] = []
        if not group["is_multi_beam"]:
            reasons.append("Single beam group")
            if rule_scores["sketch_span"] >= 80:
                reasons.append("Coherent detail sketches")
            return reasons

        if detail_cluster_count == 1:
            reasons.append("Continuous reinforcement detail envelope")
        else:
            reasons.append("Independent sketches detected across members")

        if rule_scores["shared_annotations"] >= 75:
            reasons.append("Shared engineering annotations present")
        if rule_scores["geometry_similarity"] >= 75:
            reasons.append("Similar sketch geometry across members")
        if rule_scores["alignment"] >= 75:
            reasons.append("Aligned detail bands")
        if rule_scores["title_pattern"] >= 75:
            reasons.append("Beam titles within detail region")
        return reasons

    def _recommendation(
        self,
        group: BeamGroup,
        score: int,
        rule_scores: Dict[str, float],
    ) -> str:
        if not group["is_multi_beam"]:
            return "KEEP" if score >= 60 else "REVIEW"
        if score >= 85:
            return "KEEP — excellent shared ownership candidate"
        if score < 60 or rule_scores["sketch_span"] < 45:
            return "SPLIT into individual beam groups"
        return "REVIEW — moderate confidence"


def expand_detail_band(band: Dict[str, float]) -> Dict[str, float]:
    margin = TITLE_INSIDE_DETAIL_MARGIN_MM
    return {
        "xmin": band["xmin"] - margin,
        "ymin": band["ymin"] - margin,
        "xmax": band["xmax"] + margin,
        "ymax": band["ymax"] + margin,
    }
