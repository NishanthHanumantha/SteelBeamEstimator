"""Phase D.3.3 — validate reconciled annotation ownership."""

from typing import Any, Dict, List, Literal, Set

from src.framing.beam_geometry import beam_mark_sort_key

ValidationStatus = Literal["PASS", "WARN", "FAIL"]


class OwnershipValidator:
    """Validate ownership reconciliation results."""

    def validate(
        self,
        master: List[dict[str, Any]],
        detail_regions: List[dict[str, Any]],
    ) -> Dict[str, Any]:
        region_titles = {
            r["region_id"]: {str(t).upper() for t in r["beam_titles"]}
            for r in detail_regions
        }
        region_ids = set(region_titles.keys())

        owned = [m for m in master if m["ownership_status"] == "OWNED"]
        ambiguous = [m for m in master if m["ownership_status"] == "AMBIGUOUS"]
        unassigned = [m for m in master if m["ownership_status"] == "UNASSIGNED"]

        multi_region: List[str] = []
        seen_region: Dict[str, str] = {}
        for record in owned:
            ann_id = record["annotation_id"]
            region_id = record.get("detail_region_id")
            if ann_id in seen_region and seen_region[ann_id] != region_id:
                multi_region.append(ann_id)
            if region_id:
                seen_region[ann_id] = region_id

        contamination: List[dict[str, Any]] = []
        cross_region: List[dict[str, Any]] = []

        for region in detail_regions:
            region_id = region["region_id"]
            allowed = region_titles[region_id]
            region_records = [
                m for m in owned if m.get("detail_region_id") == region_id
            ]
            foreign = [
                m
                for m in region_records
                if str(m.get("resolved_beam_mark", "")).upper() not in allowed
            ]
            if foreign:
                contamination.append(
                    {
                        "region_id": region_id,
                        "beam_titles": sorted(allowed, key=beam_mark_sort_key),
                        "foreign_count": len(foreign),
                        "foreign_beam_marks": sorted(
                            {
                                str(m["resolved_beam_mark"]).upper()
                                for m in foreign
                            },
                            key=beam_mark_sort_key,
                        ),
                        "sample_annotation_ids": [m["annotation_id"] for m in foreign[:5]],
                    }
                )

        for record in owned:
            hist = str(record.get("historical_beam_mark", "")).upper()
            resolved = str(record.get("resolved_beam_mark", "")).upper()
            region_id = record.get("detail_region_id")
            if not region_id or region_id not in region_titles:
                continue
            if hist and hist not in region_titles[region_id]:
                cross_region.append(
                    {
                        "annotation_id": record["annotation_id"],
                        "historical_beam_mark": hist,
                        "resolved_beam_mark": resolved,
                        "detail_region_id": region_id,
                        "region_beams": sorted(
                            region_titles[region_id], key=beam_mark_sort_key
                        ),
                    }
                )

        resolved_contaminations = sum(
            1
            for c in contamination
            for m in owned
            if m.get("detail_region_id") == c["region_id"]
            and str(m.get("historical_beam_mark", "")).upper()
            not in region_titles[c["region_id"]]
            and str(m.get("resolved_beam_mark", "")).upper()
            in region_titles[c["region_id"]]
        )

        warnings: List[str] = []
        if ambiguous:
            warnings.append(f"{len(ambiguous)} ambiguous ownership case(s)")
        if unassigned:
            warnings.append(f"{len(unassigned)} unassigned annotation(s)")
        if contamination:
            warnings.append(
                f"{len(contamination)} region(s) with foreign resolved beam marks"
            )

        status: ValidationStatus = "PASS"
        if ambiguous or contamination:
            status = "WARN"
        if len(unassigned) > len(master) * 0.1:
            status = "FAIL"

        scores = [m["confidence_score"] for m in master if m["confidence_score"]]
        avg_conf = sum(scores) / len(scores) if scores else 0.0

        parser_ready = (
            status != "FAIL"
            and not contamination
            and len(unassigned) == 0
        )

        return {
            "status": status,
            "total_annotations": len(master),
            "owned_count": len(owned),
            "ambiguous_count": len(ambiguous),
            "unassigned_count": len(unassigned),
            "ownership_conflict_count": len(ambiguous),
            "average_confidence": round(avg_conf, 1),
            "contamination_cases": contamination,
            "cross_region_historical_cases": cross_region,
            "resolved_contamination_count": resolved_contaminations,
            "multi_region_assignments": multi_region,
            "warnings": warnings,
            "parser_ready": parser_ready,
            "region_coverage": {
                region_id: len(
                    [m for m in owned if m.get("detail_region_id") == region_id]
                )
                for region_id in sorted(region_ids)
            },
        }
