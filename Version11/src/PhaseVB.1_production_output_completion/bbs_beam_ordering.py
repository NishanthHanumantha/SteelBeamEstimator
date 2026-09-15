"""
V11.1 — BBS drawing-layout beam ordering (presentation layer only).

Reorders existing BBS beam groups to match the reinforcement drawing:

    visual top → bottom (drawing rows)
    within each row: visual left → right

Does not recompute quantities, lengths, roles, or steel weights.
Disable with STEEL_BBS_SPATIAL_ORDER=off.

Coordinate convention (verified, not assumed):
    Version11 M.1 CoordTransform documents DXF X right, Y up.
    Visual top = larger DXF Y. Visual left = smaller DXF X.
"""
from __future__ import annotations

import json
import logging
import os
import statistics
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger("steel_vb1.bbs_ordering")

ENV_ENABLE = "STEEL_BBS_SPATIAL_ORDER"

# DXF model space: X increases right, Y increases up (M.1 dxf_renderer.CoordTransform).
DXF_Y_INCREASES_VISUALLY_UP = True

_VROOT1_REL = Path("PhaseVROOT.1_dynamic_pipeline_initialization") / "beam_registry.json"
_L22_REL = Path("PhaseL.2.2_geometry_recovery") / "geometry_registry.json"


@dataclass(frozen=True)
class BeamPosition:
    beam_id: str
    x: float
    y: float
    source: str


@dataclass
class OrderingTrace:
    y_increases_visually_up: bool
    row_gap_threshold: Optional[float]
    rows: List[Dict[str, Any]]
    ordered_beam_ids: List[str]
    missing_geometry_beam_ids: List[str]
    fallback: Optional[str] = None
    enabled: bool = True


def spatial_order_enabled() -> bool:
    raw = (os.environ.get(ENV_ENABLE) or "on").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def visual_y(dxf_y: float, y_increases_visually_up: bool = DXF_Y_INCREASES_VISUALLY_UP) -> float:
    """Larger return value = visually higher on the drawing."""
    return float(dxf_y) if y_increases_visually_up else -float(dxf_y)


def load_beam_positions(
    *,
    run_root: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    output_root: Optional[Path] = None,
) -> Dict[str, BeamPosition]:
    """Load existing VROOT1 / L.2.2 centroids. Does not recompute geometry."""
    positions: Dict[str, BeamPosition] = {}
    for root in _candidate_output_roots(run_root, output_dir, output_root):
        vroot = root / _VROOT1_REL
        if vroot.is_file():
            _merge_vroot1(positions, vroot)
        l22 = root / _L22_REL
        if l22.is_file():
            _merge_l22(positions, l22)
    return positions


def order_beam_ids(
    beam_ids: Sequence[str],
    positions: Dict[str, BeamPosition],
    *,
    y_increases_visually_up: bool = DXF_Y_INCREASES_VISUALLY_UP,
) -> Tuple[List[str], OrderingTrace]:
    """Deterministic drawing-row order. Unknown geometry appended in original order."""
    seen = set()
    original: List[str] = []
    for bid in beam_ids:
        if bid in seen:
            continue
        seen.add(bid)
        original.append(bid)

    located = [positions[b] for b in original if b in positions]
    missing = [b for b in original if b not in positions]

    if not located:
        trace = OrderingTrace(
            y_increases_visually_up=y_increases_visually_up,
            row_gap_threshold=None,
            rows=[],
            ordered_beam_ids=list(original),
            missing_geometry_beam_ids=list(missing),
            fallback="ORIGINAL_ENCOUNTER_ORDER_NO_GEOMETRY",
        )
        if missing:
            logger.warning(
                "BBS spatial order: no usable geometry for %s beam(s); keeping original order",
                len(missing),
            )
        return list(original), trace

    rows, tau = _cluster_drawing_rows(located, y_increases_visually_up)
    ordered: List[str] = []
    row_payload: List[Dict[str, Any]] = []
    for i, row in enumerate(rows, start=1):
        row_sorted = sorted(row, key=lambda p: (p.x, p.beam_id))
        row_payload.append(
            {
                "drawing_row": i,
                "beams": [
                    {"beam_id": p.beam_id, "x": p.x, "y": p.y, "source": p.source}
                    for p in row_sorted
                ],
            }
        )
        ordered.extend(p.beam_id for p in row_sorted)

    if missing:
        logger.warning(
            "BBS spatial order: %s beam(s) missing geometry; appended in original order: %s",
            len(missing),
            ", ".join(missing),
        )
        ordered.extend(missing)

    trace = OrderingTrace(
        y_increases_visually_up=y_increases_visually_up,
        row_gap_threshold=tau,
        rows=row_payload,
        ordered_beam_ids=ordered,
        missing_geometry_beam_ids=missing,
        fallback="APPEND_ORIGINAL_ORDER" if missing else None,
    )
    return ordered, trace


def reorder_bbs_rows(
    rows: Sequence[Any],
    ordered_beam_ids: Sequence[str],
) -> List[Any]:
    """Move complete beam groups. Preserve within-beam row sequence. Renumber header si_no."""
    groups: Dict[str, List[Any]] = {}
    group_order: List[str] = []
    for row in rows:
        bid = str(getattr(row, "beam_id", "") or "")
        if bid not in groups:
            groups[bid] = []
            group_order.append(bid)
        groups[bid].append(row)

    rank = {bid: i for i, bid in enumerate(ordered_beam_ids)}
    # Beams not in the sequence keep relative order after ranked beams.
    extra = [b for b in group_order if b not in rank]
    final_ids = [b for b in ordered_beam_ids if b in groups] + extra

    out: List[Any] = []
    header_si = 1
    for bid in final_ids:
        for row in groups[bid]:
            if getattr(row, "is_beam_header", False):
                out.append(replace(row, si_no=header_si))
                header_si += 1
            else:
                out.append(row)
    return out


def bbs_row_identity(row: Any) -> Tuple[Any, ...]:
    """Identity for invariant checks. Excludes presentation si_no."""
    return (
        str(getattr(row, "beam_id", "") or ""),
        bool(getattr(row, "is_beam_header", False)),
        getattr(row, "description", None),
        getattr(row, "frame_type", None),
        getattr(row, "diameter_mm", None),
        getattr(row, "spacing_m", None),
        getattr(row, "quantity", None),
        getattr(row, "dvlp_length_m", None),
        getattr(row, "cut_length_m", None),
        getattr(row, "total_length_m", None),
        getattr(row, "weight_d8", None),
        getattr(row, "weight_d10", None),
        getattr(row, "weight_d12", None),
        getattr(row, "weight_d16", None),
        getattr(row, "weight_d20", None),
        getattr(row, "weight_d25", None),
        getattr(row, "weight_d32", None),
        getattr(row, "total_weight_kg", None),
    )


def assert_bbs_invariants(before: Sequence[Any], after: Sequence[Any]) -> None:
    if len(before) != len(after):
        raise AssertionError(f"BBS row count changed: {len(before)} -> {len(after)}")
    b_ids = [bbs_row_identity(r) for r in before]
    a_ids = [bbs_row_identity(r) for r in after]
    if sorted(b_ids, key=repr) != sorted(a_ids, key=repr):
        raise AssertionError("BBS row multiset changed after spatial reorder")

    def _groups(rows: Sequence[Any]) -> Dict[str, List[Tuple[Any, ...]]]:
        g: Dict[str, List[Tuple[Any, ...]]] = {}
        for row in rows:
            bid = str(getattr(row, "beam_id", "") or "")
            g.setdefault(bid, []).append(bbs_row_identity(row))
        return g

    gb, ga = _groups(before), _groups(after)
    if set(gb) != set(ga):
        raise AssertionError("BBS beam membership changed")
    for bid, seq in gb.items():
        if ga[bid] != seq:
            raise AssertionError(f"Within-beam BBS sequence changed for {bid}")


def apply_bbs_drawing_order(
    rows: Sequence[Any],
    *,
    run_root: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    output_root: Optional[Path] = None,
    positions: Optional[Dict[str, BeamPosition]] = None,
    y_increases_visually_up: bool = DXF_Y_INCREASES_VISUALLY_UP,
    enabled: Optional[bool] = None,
) -> Tuple[List[Any], OrderingTrace]:
    """Presentation-layer entry point used by VB.1."""
    row_list = list(rows)
    if enabled is None:
        enabled = spatial_order_enabled()
    if not enabled:
        ids = _unique_beam_ids(row_list)
        trace = OrderingTrace(
            y_increases_visually_up=y_increases_visually_up,
            row_gap_threshold=None,
            rows=[],
            ordered_beam_ids=ids,
            missing_geometry_beam_ids=[],
            fallback="DISABLED",
            enabled=False,
        )
        return row_list, trace

    if positions is None:
        positions = load_beam_positions(
            run_root=run_root, output_dir=output_dir, output_root=output_root
        )
    ordered, trace = order_beam_ids(
        _unique_beam_ids(row_list),
        positions,
        y_increases_visually_up=y_increases_visually_up,
    )
    reordered = reorder_bbs_rows(row_list, ordered)
    assert_bbs_invariants(row_list, reordered)
    _log_trace(trace)
    return reordered, trace


def format_ordering_trace(trace: OrderingTrace) -> str:
    lines = ["BBS drawing-order trace:"]
    lines.append(f"  DXF Y increases visually up: {trace.y_increases_visually_up}")
    if trace.row_gap_threshold is not None:
        lines.append(f"  Row-gap threshold: {trace.row_gap_threshold:.3f}")
    if trace.fallback:
        lines.append(f"  Fallback: {trace.fallback}")
    for row in trace.rows:
        idx = row["drawing_row"]
        lines.append(f"  Drawing row {idx}:")
        for beam in row["beams"]:
            lines.append(
                f"      {beam['beam_id']}  -> X={beam['x']:.2f}  Y={beam['y']:.2f}"
            )
    if trace.missing_geometry_beam_ids:
        lines.append(
            "  Missing geometry (appended): "
            + ", ".join(trace.missing_geometry_beam_ids)
        )
    return "\n".join(lines)


def trace_to_dict(trace: OrderingTrace) -> Dict[str, Any]:
    return {
        "enabled": trace.enabled,
        "y_increases_visually_up": trace.y_increases_visually_up,
        "row_gap_threshold": trace.row_gap_threshold,
        "fallback": trace.fallback,
        "ordered_beam_ids": trace.ordered_beam_ids,
        "missing_geometry_beam_ids": trace.missing_geometry_beam_ids,
        "rows": trace.rows,
        "coordinate_convention": (
            "DXF X increases right; DXF Y increases up "
            "(Version11 M.1 CoordTransform). Visual top = larger Y."
        ),
    }


def _cluster_drawing_rows(
    located: Sequence[BeamPosition],
    y_increases_visually_up: bool,
) -> Tuple[List[List[BeamPosition]], float]:
    pts = sorted(
        located,
        key=lambda p: (-visual_y(p.y, y_increases_visually_up), p.x, p.beam_id),
    )
    if len(pts) == 1:
        return [list(pts)], 0.0

    vis = [visual_y(p.y, y_increases_visually_up) for p in pts]
    gaps = [vis[i] - vis[i + 1] for i in range(len(vis) - 1)]
    pos_gaps = [g for g in gaps if g > 1e-9]
    if not pos_gaps:
        return [list(pts)], 0.0

    x_span = max(p.x for p in pts) - min(p.x for p in pts)
    y_span = max(vis) - min(vis)
    tau = _row_gap_threshold(pos_gaps, x_span, y_span)

    rows: List[List[BeamPosition]] = [[pts[0]]]
    for i, p in enumerate(pts[1:], start=1):
        if gaps[i - 1] <= tau:
            rows[-1].append(p)
        else:
            rows.append([p])
    return rows, float(tau)


def _row_gap_threshold(pos_gaps: Sequence[float], x_span: float, y_span: float) -> float:
    """Scale-aware split between within-row Y jitter and between-row pitch.

    When consecutive Y gaps are strongly bimodal (typical multi-row sheets),
    the small mode is within-row scatter. When gaps are similar, fall back to
    layout aspect: a wide/short cloud is one row; otherwise split on large drops.
    """
    median_g = statistics.median(pos_gaps)
    max_g = max(pos_gaps)
    ratio = max_g / max(median_g, 1e-9)
    if ratio >= 4.0:
        return max(8.0 * median_g, 0.15 * (median_g + max_g))
    if y_span <= 0.20 * max(x_span, 1e-9):
        return y_span + 1.0
    return 0.5 * max_g


def _unique_beam_ids(rows: Sequence[Any]) -> List[str]:
    seen = set()
    ids: List[str] = []
    for row in rows:
        bid = str(getattr(row, "beam_id", "") or "")
        if not bid or bid in seen:
            continue
        seen.add(bid)
        ids.append(bid)
    return ids


def _candidate_output_roots(
    run_root: Optional[Path],
    output_dir: Optional[Path],
    output_root: Optional[Path],
) -> List[Path]:
    roots: List[Path] = []
    env_out = (os.environ.get("STEEL_OUTPUT_ROOT") or "").strip()
    env_run = (os.environ.get("STEEL_RUN_ROOT") or "").strip()
    if output_root is not None:
        roots.append(Path(output_root))
    if env_out:
        roots.append(Path(env_out))
    if output_dir is not None:
        roots.append(Path(output_dir).resolve().parent)
    if run_root is not None:
        roots.append(Path(run_root) / "data" / "output")
    if env_run:
        roots.append(Path(env_run) / "data" / "output")
    unique: List[Path] = []
    seen = set()
    for root in roots:
        try:
            key = str(root.resolve()) if root.exists() else str(root)
        except OSError:
            key = str(root)
        if key in seen:
            continue
        seen.add(key)
        unique.append(root)
    return unique


def _merge_vroot1(positions: Dict[str, BeamPosition], path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    beams = data.get("beams") if isinstance(data, dict) else None
    if not isinstance(beams, dict):
        return
    for bid, rec in beams.items():
        if not isinstance(rec, dict):
            continue
        pos = _position_from_record(str(bid), rec, source=f"vroot1:{path}")
        if pos is not None and pos.beam_id not in positions:
            positions[pos.beam_id] = pos


def _merge_l22(positions: Dict[str, BeamPosition], path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return
    for rec in entries:
        if not isinstance(rec, dict):
            continue
        bid = str(rec.get("beam_id") or "")
        payload = {
            "centroid_x": rec.get("dxf_centroid_x"),
            "centroid_y": rec.get("dxf_centroid_y"),
            "bbox": rec.get("dxf_bbox") or rec.get("bounding_box"),
        }
        pos = _position_from_record(bid, payload, source=f"l22:{path}")
        if pos is not None and pos.beam_id not in positions:
            positions[pos.beam_id] = pos


def _position_from_record(beam_id: str, rec: Dict[str, Any], *, source: str) -> Optional[BeamPosition]:
    if not beam_id:
        return None
    cx, cy = rec.get("centroid_x"), rec.get("centroid_y")
    if cx is not None and cy is not None:
        try:
            return BeamPosition(beam_id, float(cx), float(cy), source)
        except (TypeError, ValueError):
            pass
    bbox = rec.get("bbox")
    if isinstance(bbox, dict):
        try:
            x_min, x_max = float(bbox["x_min"]), float(bbox["x_max"])
            y_min, y_max = float(bbox["y_min"]), float(bbox["y_max"])
            return BeamPosition(
                beam_id,
                (x_min + x_max) / 2.0,
                (y_min + y_max) / 2.0,
                source + ":bbox_center",
            )
        except (KeyError, TypeError, ValueError):
            return None
    return None


def _log_trace(trace: OrderingTrace) -> None:
    logger.info(format_ordering_trace(trace))
    print(format_ordering_trace(trace))
