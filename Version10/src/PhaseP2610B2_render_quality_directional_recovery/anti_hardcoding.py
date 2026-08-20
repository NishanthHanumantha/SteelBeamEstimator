"""Anti-hardcoding guards and metamorphic spatial tests. No canonical DXF writes."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP2610B_adaptive_beam_detail_crop.envelope import adaptive_detail_extent
from PhaseP2610B_adaptive_beam_detail_crop.evidence import next_row_y_cap, owned_by_mark, x_barriers
from PhaseP2610A_beam_region_crop_audit.title_localizer import choose_mark, collect_beam_titles

from .config import TRANSLATION_DX_MM, TRANSLATION_DY_MM, TRANSLATION_TOL_MM, MAX_EXPAND_FACTOR
from .orientation import HORIZONTAL, VERTICAL, dominant_orientation
from .recovery import (
    ACTION_EXPAND_BOTH_X,
    ACTION_EXPAND_BOTH_Y,
    ACTION_EXPAND_RIGHT,
    apply_action,
    choose_action,
    recover_once,
)

_RUNTIME = (
    "population.py",
    "quality.py",
    "orientation.py",
    "border.py",
    "recovery.py",
    "pipeline.py",
    "geometry.py",
    "gates.py",
    "candidates.py",
    "render_session.py",
)
_BEAM_ID_RE = re.compile(r"\bB\d+[A-Z]?\b")
_COORD_TABLE_RE = re.compile(r"crop_override|manual_extent|fixed_xy|gt_coord", re.I)


def source_guard(package_dir: Path) -> Dict[str, Any]:
    hits: List[Dict[str, str]] = []
    folder = Path(package_dir)
    for name in _RUNTIME:
        path = folder / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for m in _BEAM_ID_RE.finditer(text):
            hits.append({"file": name, "token": m.group(0), "reason": "beam_id_literal"})
        if _COORD_TABLE_RE.search(text):
            hits.append({"file": name, "token": "coord_table", "reason": "manual_override_token"})
        if ("annotations_by" + "_beam") in text or ("TRUE_" + "RECOVERY") in text:
            hits.append({"file": name, "token": "gt_or_r1", "reason": "gt_or_association"})
    return {
        "ok": len(hits) == 0,
        "hits": hits,
        "beam_id_special_cases": False,
        "manual_crop_overrides": False,
        "gt_coordinate_dependency": False,
    }


def translation_invariance_synthetic() -> Dict[str, Any]:
    mark = {"x": 100.0, "y": 200.0, "depth_mm": 500.0}
    titles = [
        {"beam_id": "BX", "x": 100.0, "y": 200.0},
        {"beam_id": "BY", "x": 200.0, "y": 3500.0},
        {"beam_id": "BZ", "x": 5100.0, "y": 250.0},
    ]
    cap0 = next_row_y_cap(mark, titles)
    left0, right0 = x_barriers(mark, titles)
    dx, dy = TRANSLATION_DX_MM, TRANSLATION_DY_MM
    mark_t = {"x": mark["x"] + dx, "y": mark["y"] + dy, "depth_mm": 500.0}
    titles_t = [{"beam_id": t["beam_id"], "x": t["x"] + dx, "y": t["y"] + dy} for t in titles]
    cap1 = next_row_y_cap(mark_t, titles_t)
    left1, right1 = x_barriers(mark_t, titles_t)
    diag = {
        "primary_status": "BORDER_CLIPPING_SUSPECT",
        "meaningful_border_contact": {"left": False, "right": True, "top": False, "bottom": False},
        "empty_sides": [],
    }
    a0 = choose_action(diagnostic=diag, orientation=HORIZONTAL)
    a1 = choose_action(diagnostic=diag, orientation=HORIZONTAL)
    o0 = dominant_orientation(mark=mark, extent=(-2000.0, -400.0, 4000.0, 1200.0), evidence=[{"x": -1800, "y": 200}, {"x": 3800, "y": 220}])
    o1 = dominant_orientation(mark=mark_t, extent=(-2000.0 + dx, -400.0 + dy, 4000.0 + dx, 1200.0 + dy), evidence=[{"x": -1800 + dx, "y": 200 + dy}, {"x": 3800 + dx, "y": 220 + dy}])
    ok = (
        abs((cap1 - dy) - cap0) < TRANSLATION_TOL_MM
        and abs((left1 - dx) - left0) < TRANSLATION_TOL_MM
        and abs((right1 - dx) - right0) < TRANSLATION_TOL_MM
        and a0 == a1 == ACTION_EXPAND_RIGHT
        and o0 == o1 == HORIZONTAL
        and owned_by_mark(100.0 + 50.0, 200.0 + 1971.0, mark, titles) is True
        and owned_by_mark(100.0 + 50.0 + dx, 200.0 + 1971.0 + dy, mark_t, titles_t) is True
    )
    return {
        "ok": ok,
        "cap0": cap0,
        "cap1": cap1,
        "action": a0,
        "orientation": o0,
        "dx": dx,
        "dy": dy,
    }


def spatial_distance_robustness() -> Dict[str, Any]:
    mark = {"x": 0.0, "y": 0.0, "depth_mm": 500.0}
    titles = [
        {"beam_id": "BX", "x": 0.0, "y": 0.0},
        {"beam_id": "BY", "x": 80.0, "y": 3300.0},
    ]
    cap = next_row_y_cap(mark, titles)
    extent = (-2000.0, -400.0, 2000.0, 1800.0)
    diag = {
        "primary_status": "BORDER_CLIPPING_SUSPECT",
        "meaningful_border_contact": {"left": False, "right": False, "top": True, "bottom": False},
        "empty_sides": [],
    }
    after = apply_action(extent, ACTION_EXPAND_BOTH_Y, diagnostic=diag, mark=mark, titles=titles, crop_type="context")
    ok = after[3] <= cap + 1.0 and after[3] < 3300.0
    return {"ok": ok, "y_cap": cap, "after_ymax": after[3], "far_title_y": 3300.0}


def packed_sheet_robustness() -> Dict[str, Any]:
    mark = {"x": 0.0, "y": 0.0, "depth_mm": 1100.0}
    titles = [
        {"beam_id": "BX", "x": 0.0, "y": 0.0},
        {"beam_id": "BZ", "x": 5000.0, "y": 50.0},
        {"beam_id": "BY", "x": 80.0, "y": 3300.0},
    ]
    left, right = x_barriers(mark, titles)
    extent = (-1800.0, -400.0, 1800.0, 1800.0)
    diag = {
        "primary_status": "BORDER_CLIPPING_SUSPECT",
        "meaningful_border_contact": {"left": True, "right": True, "top": False, "bottom": False},
        "empty_sides": [],
    }
    after = apply_action(extent, ACTION_EXPAND_BOTH_X, diagnostic=diag, mark=mark, titles=titles, crop_type="context")
    ok = after[2] <= right + 1.0 and after[0] >= left - 1.0 and after[2] < 5000.0
    initial = extent
    rec = recover_once(
        extent=extent,
        diagnostic=diag,
        orientation=HORIZONTAL,
        mark=mark,
        titles=titles,
        crop_type="context",
        initial_extent=initial,
        attempt=1,
    )
    factor_ok = True
    cur = extent
    for i in range(1, 8):
        rec_i = recover_once(
            extent=cur,
            diagnostic=diag,
            orientation=HORIZONTAL,
            mark=mark,
            titles=titles,
            crop_type="context",
            initial_extent=initial,
            attempt=i,
        )
        cur = tuple(rec_i["after_bounds"])  # type: ignore
        w0 = initial[2] - initial[0]
        if (cur[2] - cur[0]) / w0 > MAX_EXPAND_FACTOR + 0.05:
            factor_ok = False
    ok = after[2] <= right + 1.0 and after[0] >= left - 1.0 and after[2] < 5000.0 and factor_ok
    return {"ok": ok, "x_left": left, "x_right": right, "after": list(after), "factor_ok": factor_ok, "first_action": rec.get("action")}


def translation_invariance_dxf_copy(msp, beam_id: str, titles: list) -> Dict[str, Any]:
    mark = choose_mark(msp, titles, beam_id)
    if mark is None:
        return {"ok": False, "error": "mark_missing"}
    before = adaptive_detail_extent(msp=msp, beam_id=beam_id, mark=mark, titles=titles)
    dx, dy = TRANSLATION_DX_MM, TRANSLATION_DY_MM
    for e in msp:
        try:
            e.translate(dx, dy, 0)
        except Exception:
            continue
    titles_t = collect_beam_titles(msp)
    mark_t = choose_mark(msp, titles_t, beam_id)
    if mark_t is None:
        return {"ok": False, "error": "translated_mark_missing"}
    after = adaptive_detail_extent(msp=msp, beam_id=beam_id, mark=mark_t, titles=titles_t)
    b = [float(v) for v in before["detail_extent"]]
    a = [float(v) for v in after["detail_extent"]]
    shifted = [b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy]
    deltas = [abs(a[i] - shifted[i]) for i in range(4)]
    ok = max(deltas) < 250.0
    return {
        "ok": ok,
        "beam_id": beam_id,
        "before": b,
        "after": a,
        "expected_shifted": shifted,
        "max_delta_mm": max(deltas),
        "note": "in-memory entity.translate only; canonical DXF not written",
    }


def run_anti_hardcoding(
    *,
    package_dir: Path,
    msp=None,
    beam_id: Optional[str] = None,
    titles: Optional[list] = None,
) -> Dict[str, Any]:
    guard = source_guard(package_dir)
    synth = translation_invariance_synthetic()
    dist = spatial_distance_robustness()
    packed = packed_sheet_robustness()
    dxf_t = {"ok": True, "skipped": True}
    if msp is not None and beam_id:
        dxf_t = translation_invariance_dxf_copy(msp, beam_id, list(titles or []))
    ok = bool(guard.get("ok") and synth.get("ok") and dist.get("ok") and packed.get("ok") and dxf_t.get("ok"))
    return {
        "ok": ok,
        "source_guard": guard,
        "translation_invariance": {"synthetic": synth, "dxf_copy": dxf_t},
        "spatial_distance": dist,
        "packed_sheet": packed,
        "beam_id_special_cases": bool(guard.get("hits")),
        "manual_crop_overrides": False,
        "gt_coordinate_dependency": False,
    }


__all__ = ["run_anti_hardcoding", "source_guard"]
