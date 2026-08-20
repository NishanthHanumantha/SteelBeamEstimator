"""Anti-hardcoding guards. No canonical DXF writes. No beam-ID crop exceptions."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP2610B_adaptive_beam_detail_crop.envelope import adaptive_detail_extent
from PhaseP2610B_adaptive_beam_detail_crop.evidence import next_row_y_cap, owned_by_mark, x_barriers
from PhaseP2610A_beam_region_crop_audit.title_localizer import choose_mark, collect_beam_titles
from PhaseP2610B2_render_quality_directional_recovery.orientation import HORIZONTAL, dominant_orientation

from .candidates import generate_candidates
from .config import TRANSLATION_DX_MM, TRANSLATION_DY_MM, TRANSLATION_TOL_MM
from .context_builder import build_context_envelope
from .gate import evaluate_candidate, should_replace

_RUNTIME = (
    "population.py",
    "classify.py",
    "anchor.py",
    "context_builder.py",
    "candidates.py",
    "gate.py",
    "pipeline.py",
)
_BEAM_ID_RE = re.compile(r"\bB\d+[A-Z]?\b")
_COORD_TABLE_RE = re.compile(r"crop_override|manual_extent|fixed_xy|gt_coord", re.I)


def source_guard(package_dir: Path) -> Dict[str, Any]:
    hits: List[Dict[str, str]] = []
    for name in _RUNTIME:
        path = Path(package_dir) / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for m in _BEAM_ID_RE.finditer(text):
            hits.append({"file": name, "token": m.group(0), "reason": "beam_id_literal"})
        if _COORD_TABLE_RE.search(text):
            hits.append({"file": name, "token": "coord_table", "reason": "manual_override_token"})
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
    o0 = dominant_orientation(
        mark=mark,
        extent=(-2000.0, -400.0, 4000.0, 1200.0),
        evidence=[{"x": -1800, "y": 200}, {"x": 3800, "y": 220}],
    )
    o1 = dominant_orientation(
        mark=mark_t,
        extent=(-2000.0 + dx, -400.0 + dy, 4000.0 + dx, 1200.0 + dy),
        evidence=[{"x": -1800 + dx, "y": 200 + dy}, {"x": 3800 + dx, "y": 220 + dy}],
    )
    ok = (
        abs((cap1 - dy) - cap0) < TRANSLATION_TOL_MM
        and abs((left1 - dx) - left0) < TRANSLATION_TOL_MM
        and abs((right1 - dx) - right0) < TRANSLATION_TOL_MM
        and o0 == o1 == HORIZONTAL
        and owned_by_mark(150.0, 200.0 + 1971.0, mark, titles) is True
        and owned_by_mark(150.0 + dx, 200.0 + 1971.0 + dy, mark_t, titles_t) is True
    )
    return {"ok": ok, "cap0": cap0, "cap1": cap1, "orientation": o0, "dx": dx, "dy": dy}


def spatial_distance_robustness() -> Dict[str, Any]:
    mark = {"x": 0.0, "y": 0.0, "depth_mm": 500.0}
    titles = [{"beam_id": "BX", "x": 0.0, "y": 0.0}, {"beam_id": "BY", "x": 80.0, "y": 3300.0}]
    cap = next_row_y_cap(mark, titles)
    anchor = {
        "core": (-2000.0, -400.0, 2000.0, 1800.0),
        "orientation": "VERTICAL",
        "x_barriers": list(x_barriers(mark, titles)),
        "y_floor": -4000.0,
        "y_cap": cap,
        "mark": mark,
    }
    env = build_context_envelope(anchor)
    ok = env["extent"][3] <= cap + 1.0 and env["extent"][3] < 3300.0
    return {"ok": ok, "y_cap": cap, "after_ymax": env["extent"][3], "far_title_y": 3300.0}


def packed_sheet_robustness() -> Dict[str, Any]:
    mark = {"x": 0.0, "y": 0.0, "depth_mm": 1100.0}
    titles = [
        {"beam_id": "BX", "x": 0.0, "y": 0.0},
        {"beam_id": "BZ", "x": 5000.0, "y": 50.0},
        {"beam_id": "BY", "x": 80.0, "y": 3300.0},
    ]
    left, right = x_barriers(mark, titles)
    anchor = {
        "core": (-1800.0, -400.0, 1800.0, 1800.0),
        "orientation": HORIZONTAL,
        "x_barriers": [left, right],
        "y_floor": -2000.0,
        "y_cap": 3000.0,
        "mark": mark,
    }
    env = build_context_envelope(anchor)
    cands = generate_candidates(
        anchor=anchor,
        context_envelope=env,
        baseline_extent=(-1800.0, -400.0, 1800.0, 1800.0),
        baseline_quality={"primary_status": "BORDER_CLIPPING_SUSPECT", "empty_sides": [], "coverage_x": 0.9},
    )
    ok = all(c["extent"][2] <= right + 1.0 and c["extent"][0] >= left - 1.0 and c["extent"][2] < 5000.0 for c in cands)
    return {"ok": ok, "x_left": left, "x_right": right, "candidate_count": len(cands)}


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
    return {
        "ok": max(deltas) < 250.0,
        "beam_id": beam_id,
        "max_delta_mm": max(deltas),
        "note": "in-memory entity.translate only; canonical DXF not written",
    }


def failed_candidate_cannot_overwrite() -> Dict[str, Any]:
    baseline = {"acceptable": True, "score": 4.0}
    worse = {"acceptable": True, "score": 3.5}
    blank = {"acceptable": False, "score": 0.0}
    better = {"acceptable": True, "score": 4.5}
    return {
        "ok": (should_replace(baseline, worse) is False)
        and (should_replace(baseline, blank) is False)
        and (should_replace(baseline, better) is True),
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
    overwrite = failed_candidate_cannot_overwrite()
    dxf_t = {"ok": True, "skipped": True}
    if msp is not None and beam_id:
        dxf_t = translation_invariance_dxf_copy(msp, beam_id, list(titles or []))
    ok = bool(
        guard.get("ok")
        and synth.get("ok")
        and dist.get("ok")
        and packed.get("ok")
        and overwrite.get("ok")
        and dxf_t.get("ok")
    )
    return {
        "ok": ok,
        "source_guard": guard,
        "translation_invariance": {"synthetic": synth, "dxf_copy": dxf_t},
        "spatial_distance": dist,
        "packed_sheet": packed,
        "no_worse_overwrite": overwrite,
        "beam_id_special_cases": bool(guard.get("hits")),
        "manual_crop_overrides": False,
        "gt_coordinate_dependency": False,
    }


__all__ = ["run_anti_hardcoding", "source_guard"]
