"""Sketch linkage helpers for detail region detection."""

from typing import Any, Dict, FrozenSet, List, Set, Tuple

from src.utils.bbox_utils import horizontal_overlap_ratio, vertical_band_overlap_ratio

SKETCH_LINK_GAP_TOLERANCE_MM = 2000.0
SKETCH_LINK_MIN_VERTICAL_OVERLAP = 0.30
CELL_ADJACENCY_TOLERANCE_MM = 5.0

BeamMark = str
AdjacencyPairs = Set[FrozenSet[BeamMark]]


def build_cell_adjacency(
    beam_cells: List[dict[str, Any]],
) -> AdjacencyPairs:
    """Beam marks whose cells share an edge in the same row."""
    rows: Dict[int, List[dict[str, Any]]] = {}
    for cell in beam_cells:
        rows.setdefault(int(cell["row_id"]), []).append(cell)

    pairs: AdjacencyPairs = set()
    for row_cells in rows.values():
        ordered = sorted(row_cells, key=lambda c: float(c["xmin"]))
        for idx in range(1, len(ordered)):
            prev = ordered[idx - 1]
            curr = ordered[idx]
            gap = float(curr["xmin"]) - float(prev["xmax"])
            if gap <= CELL_ADJACENCY_TOLERANCE_MM:
                pairs.add(
                    frozenset(
                        {
                            str(prev["beam_mark"]).upper(),
                            str(curr["beam_mark"]).upper(),
                        }
                    )
                )
    return pairs


def sketches_link(
    sketch_a: dict[str, Any],
    sketch_b: dict[str, Any],
    cell_adjacency: AdjacencyPairs | None = None,
) -> bool:
    mark_a = str(sketch_a["beam_mark"]).upper()
    mark_b = str(sketch_b["beam_mark"]).upper()
    if mark_a != mark_b:
        if cell_adjacency is not None:
            if frozenset({mark_a, mark_b}) not in cell_adjacency:
                return False

    bbox_a = sketch_a["bbox"]
    bbox_b = sketch_b["bbox"]
    if horizontal_overlap_ratio(bbox_a, bbox_b) > 0.01:
        return True
    if vertical_band_overlap_ratio(bbox_a, bbox_b) < SKETCH_LINK_MIN_VERTICAL_OVERLAP:
        return False
    gap_ab = bbox_b["xmin"] - bbox_a["xmax"]
    gap_ba = bbox_a["xmin"] - bbox_b["xmax"]
    return (
        -50.0 <= gap_ab <= SKETCH_LINK_GAP_TOLERANCE_MM
        or -50.0 <= gap_ba <= SKETCH_LINK_GAP_TOLERANCE_MM
    )


def sketch_clusters(
    sketches: List[dict[str, Any]],
    cell_adjacency: AdjacencyPairs | None = None,
) -> List[List[dict[str, Any]]]:
    if not sketches:
        return []
    clusters: List[List[dict[str, Any]]] = []
    for sketch in sketches:
        placed = False
        for cluster in clusters:
            if any(
                sketches_link(sketch, other, cell_adjacency) for other in cluster
            ):
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
                    sketches_link(a, b, cell_adjacency)
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


def cluster_sketch_ids(clusters: List[List[dict[str, Any]]]) -> List[List[str]]:
    return [[str(s["sketch_id"]) for s in cluster] for cluster in clusters]
