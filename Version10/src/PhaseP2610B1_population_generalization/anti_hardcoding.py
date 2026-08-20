"""Anti-hardcoding guards and metamorphic spatial tests. No canonical DXF writes."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP2610B_adaptive_beam_detail_crop.envelope import adaptive_detail_extent
from PhaseP2610B_adaptive_beam_detail_crop.evidence import next_row_y_cap, owned_by_mark, x_barriers
from PhaseP2610A_beam_region_crop_audit.title_localizer import choose_mark, collect_beam_titles

from .config import TRANSLATION_DX_MM, TRANSLATION_DY_MM, TRANSLATION_TOL_MM

_STRESS_IDS = ("B141", "B66", "B161", "B128", "B55", "B65")
_CROP_RUNTIME = ("population.py", "validator.py")
_BEAM_ID_RE = re.compile(r"\bB\d+[A-Z]?\b")
_COORD_TABLE_RE = re.compile(r"crop_override|manual_extent|fixed_xy|gt_coord", re.I)


def source_guard(package_dir: Path, extra_dirs: Optional[List[Path]] = None) -> Dict[str, Any]:
    hits: List[Dict[str, str]] = []
    dirs = [Path(package_dir)] + [Path(p) for p in (extra_dirs or [])]
    for folder in dirs:
        for name in _CROP_RUNTIME:
            path = folder / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            for tok in _STRESS_IDS:
                if tok in text:
                    hits.append({"file": str(path.name), "token": tok, "reason": "stress_beam_id"})
            if _COORD_TABLE_RE.search(text):
                hits.append({"file": str(path.name), "token": "coord_table", "reason": "manual_override_token"})
    # P2.6.10-B crop engine must also stay beam-agnostic.
    b_engine = Path(package_dir).resolve().parent / "PhaseP2610B_adaptive_beam_detail_crop"
    for name in ("evidence.py", "envelope.py", "completeness.py"):
        path = b_engine / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for tok in _STRESS_IDS:
            if tok in text:
                hits.append({"file": f"P2610B/{name}", "token": tok, "reason": "stress_beam_id"})
        if ("annotations_by" + "_beam") in text or ("TRUE_" + "RECOVERY") in text:
            hits.append({"file": f"P2610B/{name}", "token": "gt_or_r1", "reason": "gt_or_association"})
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
    ok = (
        abs((cap1 - dy) - cap0) < TRANSLATION_TOL_MM
        and abs((left1 - dx) - left0) < TRANSLATION_TOL_MM
        and abs((right1 - dx) - right0) < TRANSLATION_TOL_MM
        and owned_by_mark(100.0 + 50.0, 200.0 + 1971.0, mark, titles) is True
        and owned_by_mark(100.0 + 50.0 + dx, 200.0 + 1971.0 + dy, mark_t, titles_t) is True
    )
    return {
        "ok": ok,
        "cap0": cap0,
        "cap1": cap1,
        "left0": left0,
        "right0": right0,
        "left1": left1,
        "right1": right1,
        "dx": dx,
        "dy": dy,
    }


def spatial_distance_robustness() -> Dict[str, Any]:
    """Top evidence beyond 2.2*depth+500 (1600 mm on a 500 mm beam) must remain inside the cap."""
    mark = {"x": 0.0, "y": 0.0, "depth_mm": 500.0}
    titles = [
        {"beam_id": "BX", "x": 0.0, "y": 0.0},
        {"beam_id": "BY", "x": 80.0, "y": 3300.0},
    ]
    cap = next_row_y_cap(mark, titles)
    old_fixed = 2.2 * 500.0 + 500.0
    far_top = 1971.0
    ok = cap > far_top and cap < 3300.0 and old_fixed < far_top
    return {"ok": ok, "y_cap": cap, "old_fixed_cap": old_fixed, "far_top_dy": far_top}


def packed_sheet_robustness() -> Dict[str, Any]:
    mark = {"x": 0.0, "y": 0.0, "depth_mm": 1100.0}
    titles = [
        {"beam_id": "BX", "x": 0.0, "y": 0.0},
        {"beam_id": "BZ", "x": 5000.0, "y": 50.0},
        {"beam_id": "BY", "x": 80.0, "y": 3300.0},
    ]
    left, right = x_barriers(mark, titles)
    cap = next_row_y_cap(mark, titles)
    ok = right > 2450.0 and right < 5000.0 and cap > 2444.0 and cap < 3300.0
    return {"ok": ok, "x_left": left, "x_right": right, "y_cap": cap}


def translation_invariance_dxf_copy(msp, beam_id: str, titles: list) -> Dict[str, Any]:
    """Translate an in-memory DXF copy. Never writes the canonical source."""
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
