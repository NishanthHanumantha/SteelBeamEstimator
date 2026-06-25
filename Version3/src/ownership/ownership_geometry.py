"""Phase D.3.3 — geometry prep for ownership (cell-filtered sketches)."""

from copy import deepcopy
from typing import Any, Dict, List

from loguru import logger

from src.utils.bbox_utils import union_bbox

SKETCH_CELL_MARGIN_MM = 800.0


def filter_region_sketches_to_cells(
    regions: List[dict[str, Any]],
    beam_cells: List[dict[str, Any]],
) -> List[dict[str, Any]]:
    """Drop member sketches whose center lies outside the owning beam cell."""
    cell_by_mark = {str(c["beam_mark"]).upper(): c for c in beam_cells}
    prepared: List[dict[str, Any]] = []
    dropped = 0

    for region in regions:
        region_copy = deepcopy(region)
        kept: List[dict[str, Any]] = []
        for sketch in region.get("member_sketches", []):
            mark = str(sketch["beam_mark"]).upper()
            cell = cell_by_mark.get(mark)
            if cell is None:
                kept.append(sketch)
                continue
            bbox = sketch["bbox"]
            cx = (float(bbox["xmin"]) + float(bbox["xmax"])) / 2.0
            xmin = float(cell["xmin"]) - SKETCH_CELL_MARGIN_MM
            xmax = float(cell["xmax"]) + SKETCH_CELL_MARGIN_MM
            if xmin <= cx <= xmax:
                kept.append(sketch)
            else:
                dropped += 1
        region_copy["member_sketches"] = kept
        if kept:
            sketch_bbox = union_bbox([s["bbox"] for s in kept])
            region_copy["sketch_bbox"] = sketch_bbox
        prepared.append(region_copy)

    if dropped:
        logger.info(
            "Ownership prep: filtered {} leaked sketch(es) from detail regions",
            dropped,
        )
    return prepared


def find_cell_for_point(
    x: float,
    y: float,
    beam_cells: List[dict[str, Any]],
    margin_mm: float = 800.0,
) -> dict[str, Any] | None:
    """Return the beam cell containing (x, y); prefer closest column when cells overlap."""
    matches: List[dict[str, Any]] = []
    for cell in beam_cells:
        xmin = float(cell["xmin"]) - margin_mm
        xmax = float(cell["xmax"]) + margin_mm
        ymin = float(cell["ymin"]) - margin_mm
        ymax = float(cell["ymax"]) + margin_mm
        if xmin <= x <= xmax and ymin <= y <= ymax:
            matches.append(cell)
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    return min(
        matches,
        key=lambda c: abs(
            (float(c["xmin"]) + float(c["xmax"])) / 2.0 - x
        ),
    )
