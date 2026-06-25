"""Phase D.3.2 — derive beam groups from validated detail regions."""

from typing import Any, Dict, List

from src.framing.beam_geometry import beam_mark_sort_key


class BeamGroupFromRegion:
    """Beam groups are derived from detail regions (one group per region)."""

    def derive(
        self,
        regions: List[dict[str, Any]],
        beam_cells: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        cell_by_mark = {str(c["beam_mark"]).upper(): c for c in beam_cells}
        groups: List[dict[str, Any]] = []

        sorted_regions = sorted(
            regions,
            key=lambda r: beam_mark_sort_key(r["beam_titles"][0]),
        )

        for index, region in enumerate(sorted_regions, start=1):
            members = sorted(region["beam_titles"], key=beam_mark_sort_key)
            member_details: List[dict[str, Any]] = []
            sketch_ids: List[str] = []

            for mark in members:
                cell = cell_by_mark.get(mark, {})
                mark_sketches = [
                    s["sketch_id"]
                    for s in region.get("member_sketches", [])
                    if str(s["beam_mark"]).upper() == mark
                ]
                sketch_ids.extend(mark_sketches)
                member_details.append(
                    {
                        "beam_mark": mark,
                        "row_id": cell.get("row_id"),
                        "cell_bbox": {
                            "xmin": cell.get("xmin"),
                            "ymin": cell.get("ymin"),
                            "xmax": cell.get("xmax"),
                            "ymax": cell.get("ymax"),
                        }
                        if cell
                        else None,
                        "detail_band": region.get("sketch_bbox", region["bbox"]),
                        "sketch_ids": mark_sketches,
                    }
                )

            groups.append(
                {
                    "beam_group_id": f"GROUP_{index:03d}",
                    "detail_region_id": region["region_id"],
                    "members": members,
                    "member_details": member_details,
                    "bounding_box": region["bbox"],
                    "detail_band": region.get("sketch_bbox", region["bbox"]),
                    "is_multi_beam": len(members) > 1,
                    "sketch_ids": sketch_ids,
                    "confidence": region.get("confidence"),
                    "continuous": region.get("continuous"),
                }
            )
        return groups
