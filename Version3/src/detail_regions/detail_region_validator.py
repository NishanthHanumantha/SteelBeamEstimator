"""Phase D.3.2 — detail region confidence and validation."""

import math
from typing import Any, Dict, List, Literal, Set, Tuple

from src.framing.beam_geometry import beam_mark_sort_key
from src.utils.bbox_utils import horizontal_overlap_ratio
from src.utils.sketch_linking import sketch_clusters

ValidationStatus = Literal["PASS", "WARN", "FAIL"]
ConfidenceLabel = Literal["HIGH", "MEDIUM", "LOW"]


class DetailRegionValidator:
    """Validate detail regions and compute per-region confidence."""

    def validate_and_score(
        self,
        regions: List[dict[str, Any]],
        all_beam_marks: List[str],
        expanded_annotations: List[dict[str, Any]] | None = None,
    ) -> Tuple[List[dict[str, Any]], Dict[str, Any]]:
        mark_to_region: Dict[str, str] = {}
        region_results: List[dict[str, Any]] = []

        for region in regions:
            scored = self._score_region(region)
            region["confidence"] = scored["confidence_score"]
            region["continuous"] = scored["continuous"]
            region["confidence_label"] = scored["confidence_label"]
            region_results.append(scored)

            for mark in region.get("beam_titles", []):
                mark_to_region[str(mark).upper()] = region["region_id"]

        ownership_issues = self._check_beam_ownership(mark_to_region, all_beam_marks)
        overlap_issues = self._check_region_overlap(regions)
        shared_issues = self._check_shared_annotations(
            expanded_annotations or [], mark_to_region
        )
        invalid_regions = [
            r for r in region_results if r.get("status") == "INVALID_REGION"
        ]

        status: ValidationStatus = "PASS"
        warnings: List[str] = list(ownership_issues + overlap_issues + shared_issues)
        for result in region_results:
            for warning in result.get("warnings", []):
                warnings.append(f"{result['region_id']}: {warning}")

        if invalid_regions or ownership_issues:
            status = "WARN"
        if any(r["confidence_score"] < 40 for r in region_results):
            status = "FAIL"
        if len(ownership_issues) > 2:
            status = "FAIL"

        parser_ready = (
            status != "FAIL"
            and not invalid_regions
            and not ownership_issues
        )

        validation = {
            "status": status,
            "total_regions": len(regions),
            "single_beam_region_count": sum(
                1 for r in regions if len(r.get("beam_titles", [])) == 1
            ),
            "multi_beam_region_count": sum(
                1 for r in regions if len(r.get("beam_titles", [])) > 1
            ),
            "invalid_region_count": len(invalid_regions),
            "invalid_regions": [
                {
                    "region_id": r["region_id"],
                    "beam_titles": r["beam_titles"],
                }
                for r in invalid_regions
            ],
            "ownership_issues": ownership_issues,
            "overlap_issues": overlap_issues,
            "shared_annotation_issues": shared_issues,
            "warnings": warnings,
            "parser_ready": parser_ready,
            "region_results": region_results,
        }
        return region_results, validation

    def _score_region(self, region: dict[str, Any]) -> dict[str, Any]:
        sketches = region.get("member_sketches", [])
        annotations = region.get("member_annotations", [])
        beam_titles = region.get("beam_titles", [])
        cluster_count = region.get("sketch_cluster_count", 1)
        is_multi = region.get("is_multi_beam", len(beam_titles) > 1)

        continuous_linkage = cluster_count == 1 if is_multi else True
        continuous = continuous_linkage and not (
            cluster_count > 1 and is_multi and not continuous_linkage
        )
        if not is_multi:
            continuous = True

        status = "VALID"
        warnings: List[str] = []
        if cluster_count > 1 and is_multi and not continuous_linkage:
            status = "INVALID_REGION"
            warnings.append(
                "INVALID_REGION: multiple sketch clusters without continuous reinforcement"
            )

        cont_reinf = 30.0 if continuous else 0.0
        sketch_cont = self._sketch_continuity_score(cluster_count, is_multi)
        ann_cont = self._annotation_continuity_score(annotations, region.get("bbox", {}))
        leader = self._leader_consistency_score(annotations)
        title = self._title_consistency_score(beam_titles, sketches)
        dimension = self._dimension_continuity_score(annotations)
        geometry = self._geometry_similarity_score(sketches)

        total = int(
            round(cont_reinf + sketch_cont + ann_cont + leader + title + dimension + geometry)
        )
        total = max(0, min(100, total))
        label = self._confidence_label(total)

        return {
            "region_id": region["region_id"],
            "beam_titles": beam_titles,
            "confidence_score": total,
            "confidence_label": label,
            "confidence": label,
            "continuous": continuous,
            "status": status,
            "sketch_cluster_count": cluster_count,
            "is_multi_beam": is_multi,
            "component_scores": {
                "continuous_reinforcement": cont_reinf,
                "sketch_continuity": sketch_cont,
                "annotation_continuity": ann_cont,
                "leader_consistency": leader,
                "beam_title_consistency": title,
                "dimension_continuity": dimension,
                "geometry_similarity": geometry,
            },
            "warnings": warnings,
        }

    def _sketch_continuity_score(self, cluster_count: int, is_multi: bool) -> float:
        if cluster_count == 1:
            return 20.0
        if not is_multi:
            return 15.0
        return 5.0

    def _annotation_continuity_score(
        self, annotations: List[dict[str, Any]], bbox: dict[str, float]
    ) -> float:
        if not annotations or not bbox:
            return 10.0
        height = bbox["ymax"] - bbox["ymin"]
        if height <= 0:
            return 10.0
        ys = [float(a["y"]) for a in annotations]
        spread = max(ys) - min(ys)
        ratio = spread / height
        if ratio <= 0.5:
            return 15.0
        if ratio <= 0.85:
            return 10.0
        return 5.0

    def _leader_consistency_score(self, annotations: List[dict[str, Any]]) -> float:
        if len(annotations) < 2:
            return 10.0
        xs = [float(a["x"]) for a in annotations]
        mean_x = sum(xs) / len(xs)
        spread = max(xs) - min(xs)
        if spread <= 3000:
            return 10.0
        if spread <= 8000:
            return 6.0
        return 3.0

    def _title_consistency_score(
        self,
        beam_titles: List[str],
        sketches: List[dict[str, Any]],
    ) -> float:
        if not beam_titles:
            return 0.0
        sketch_marks = {str(s["beam_mark"]).upper() for s in sketches}
        matched = sum(1 for t in beam_titles if t.upper() in sketch_marks)
        ratio = matched / len(beam_titles)
        if ratio >= 1.0:
            return 10.0
        if ratio >= 0.5:
            return 6.0
        return 3.0

    def _dimension_continuity_score(self, annotations: List[dict[str, Any]]) -> float:
        dim_count = sum(
            1
            for a in annotations
            if "dimension" in str(a.get("annotation_type", "")).lower()
            or "DIM" in str(a.get("clean_text", "")).upper()
        )
        if dim_count >= 3:
            return 10.0
        if dim_count >= 1:
            return 7.0
        return 4.0

    def _geometry_similarity_score(self, sketches: List[dict[str, Any]]) -> float:
        if len(sketches) < 2:
            return 5.0
        heights = [s["bbox"]["ymax"] - s["bbox"]["ymin"] for s in sketches]
        cv = self._coefficient_of_variation(heights)
        if cv <= 0.25:
            return 5.0
        if cv <= 0.45:
            return 3.0
        return 1.0

    def _coefficient_of_variation(self, values: List[float]) -> float:
        if not values:
            return 1.0
        mean = sum(values) / len(values)
        if mean <= 0.0:
            return 1.0
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return math.sqrt(variance) / mean

    def _check_beam_ownership(
        self,
        mark_to_region: Dict[str, str],
        all_beam_marks: List[str],
    ) -> List[str]:
        issues: List[str] = []
        for mark in sorted({str(m).upper() for m in all_beam_marks}, key=beam_mark_sort_key):
            if mark not in mark_to_region:
                issues.append(f"Beam {mark} not assigned to any detail region")
        seen: Dict[str, List[str]] = {}
        for mark, region_id in mark_to_region.items():
            seen.setdefault(mark, []).append(region_id)
        for mark, region_ids in seen.items():
            if len(region_ids) > 1:
                issues.append(
                    f"Beam {mark} belongs to multiple regions: {', '.join(region_ids)}"
                )
        return issues

    def _check_region_overlap(self, regions: List[dict[str, Any]]) -> List[str]:
        issues: List[str] = []
        for i, region_a in enumerate(regions):
            for region_b in regions[i + 1:]:
                overlap = horizontal_overlap_ratio(region_a["bbox"], region_b["bbox"])
                titles_a = set(region_a.get("beam_titles", []))
                titles_b = set(region_b.get("beam_titles", []))
                if overlap > 0.6 and titles_a != titles_b and titles_a & titles_b:
                    issues.append(
                        f"Overlapping regions {region_a['region_id']} and "
                        f"{region_b['region_id']} share beams "
                        f"{sorted(titles_a & titles_b, key=beam_mark_sort_key)}"
                    )
        return issues

    def _check_shared_annotations(
        self,
        expanded: List[dict[str, Any]],
        mark_to_region: Dict[str, str],
    ) -> List[str]:
        issues: List[str] = []
        for entry in expanded:
            beams = [
                str(b).upper()
                for b in entry.get("expanded_beams", entry.get("member_beams", []))
            ]
            if len(beams) < 2:
                continue
            regions: Set[str] = set()
            for beam in beams:
                if beam in mark_to_region:
                    regions.add(mark_to_region[beam])
            if len(regions) > 1:
                issues.append(
                    f"Shared annotation expansion spans regions "
                    f"{sorted(regions)} for beams {beams}"
                )
        return issues

    def _confidence_label(self, score: int) -> ConfidenceLabel:
        if score >= 85:
            return "HIGH"
        if score >= 60:
            return "MEDIUM"
        return "LOW"
