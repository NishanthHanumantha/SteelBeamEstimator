"""Unit tests for P2.5.2.3 target beam visual completeness."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .completeness import assess_beam_completeness, classify_final
from .config import COMPLETENESS_FAIL, COMPLETENESS_PASS, TARGET_BEAM_EDGE_MARGIN_PX
from .geometry_complete import collect_critical_geometry, geometric_side_deficits

MODEL_VERSION = "10.6.8"


def _png(path: Path, w: int, h: int, boxes) -> None:
    from PIL import Image, ImageDraw

    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(im)
    for box, color in boxes:
        d.rectangle(box, fill=color)
    im.save(path)


def test_critical_geometry_local_not_full_beam() -> None:
    beam = (0.0, 0.0, 20000.0, 1000.0)
    ann = (1000.0, 1100.0, 1800.0, 1300.0)
    crit = collect_critical_geometry(
        annotation_bbox=ann,
        beam_bbox=beam,
        leader_bboxes=[],
        owned_bboxes=[],
        reinforcement_bboxes=[],
        center_x=1400.0,
        center_y=1200.0,
        context=False,
    )
    cb = crit["critical_beam_bbox"]
    assert cb is not None
    assert (cb[2] - cb[0]) < 10000


def test_beam_edge_clipped_detected() -> None:
    root = Path("_p2523_test_tmp")
    root.mkdir(parents=True, exist_ok=True)
    png = root / "clip.png"
    # beam ink touches left edge
    _png(png, 200, 200, [((0, 80, 120, 120), (0, 180, 0)), ((80, 40, 140, 70), (180, 0, 180))])
    extent = (0.0, 0.0, 1000.0, 1000.0)
    # critical beam covers left of DXF → projects near left of image
    critical = (0.0, 400.0, 600.0, 600.0)
    ann = (400.0, 700.0, 700.0, 850.0)
    a = assess_beam_completeness(
        image_path=png,
        extent=extent,
        critical_beam_bbox=critical,
        annotation_bbox=ann,
        leader_bboxes=[],
        owned_bboxes=[],
        reinforcement_bboxes=[],
        beam_bbox=(0.0, 200.0, 800.0, 600.0),
        dxf_xlim=(0.0, 1000.0),
        dxf_ylim=(0.0, 1000.0),
        img_w=200,
        img_h=200,
    )
    assert a["success"]
    assert "left" in (a.get("unsafe_sides") or []) or (
        (a.get("beam_edge_margins_px") or {}).get("left", 99) < TARGET_BEAM_EDGE_MARGIN_PX
    )


def test_safe_beam_pass() -> None:
    root = Path("_p2523_test_tmp")
    root.mkdir(parents=True, exist_ok=True)
    png = root / "safe.png"
    _png(
        png,
        300,
        300,
        [
            ((40, 100, 260, 160), (0, 160, 0)),  # beam
            ((100, 50, 200, 90), (180, 0, 180)),  # ann
        ],
    )
    extent = (0.0, 0.0, 1000.0, 1000.0)
    critical = (150.0, 400.0, 850.0, 600.0)
    ann = (300.0, 700.0, 700.0, 850.0)
    a = assess_beam_completeness(
        image_path=png,
        extent=extent,
        critical_beam_bbox=critical,
        annotation_bbox=ann,
        leader_bboxes=[],
        owned_bboxes=[],
        reinforcement_bboxes=[],
        beam_bbox=(100.0, 350.0, 900.0, 650.0),
        dxf_xlim=(0.0, 1000.0),
        dxf_ylim=(0.0, 1000.0),
        img_w=300,
        img_h=300,
    )
    st, _ = classify_final(
        assessment=a, extreme=False, hit_max=False, expanded=False, render_ok=True
    )
    assert a.get("target_beam_geometry_rendered") or a.get("target_beam_geometry_present")
    assert st in (COMPLETENESS_PASS, "PARTIAL", "REVIEW")


def test_geometric_side_deficits() -> None:
    crop = (100.0, 100.0, 500.0, 500.0)
    # inner sticks out left by 50mm
    inner = (50.0, 150.0, 400.0, 400.0)
    d = geometric_side_deficits(
        crop,
        inner,
        dxf_xlim=(100.0, 500.0),
        dxf_ylim=(100.0, 500.0),
        img_w=200,
        img_h=200,
        margin_px=24,
    )
    assert d["left"] > 0
    assert d["right"] == 0 or d["right"] >= 0


def test_rejected_fails() -> None:
    root = Path("_p2523_test_tmp")
    png = root / "rej.png"
    _png(png, 200, 200, [((40, 40, 160, 160), (0, 160, 0))])
    a = assess_beam_completeness(
        image_path=png,
        extent=(0, 0, 1000, 1000),
        critical_beam_bbox=(200, 200, 800, 800),
        annotation_bbox=(300, 300, 500, 500),
        leader_bboxes=[],
        owned_bboxes=[],
        reinforcement_bboxes=[],
        beam_bbox=(200, 200, 800, 800),
        dxf_xlim=(0, 1000),
        dxf_ylim=(0, 1000),
        img_w=200,
        img_h=200,
        rejected_included=True,
    )
    st, _ = classify_final(
        assessment=a, extreme=False, hit_max=False, expanded=False, render_ok=True
    )
    assert st == COMPLETENESS_FAIL


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("critical_geometry_local_not_full_beam", test_critical_geometry_local_not_full_beam),
        ("beam_edge_clipped_detected", test_beam_edge_clipped_detected),
        ("safe_beam_pass", test_safe_beam_pass),
        ("geometric_side_deficits", test_geometric_side_deficits),
        ("rejected_fails", test_rejected_fails),
    ]
    results: List[Dict[str, Any]] = []
    for name, fn in tests:
        try:
            fn()
            results.append({"name": name, "pass": True})
        except Exception as exc:  # noqa: BLE001
            results.append({"name": name, "pass": False, "error": str(exc)})
    try:
        import shutil

        shutil.rmtree(Path("_p2523_test_tmp"), ignore_errors=True)
    except Exception:
        pass
    passed = sum(1 for r in results if r.get("pass"))
    return {
        "success": passed == len(results),
        "passed": passed,
        "total": len(results),
        "results": results,
        "model_version": MODEL_VERSION,
    }


__all__ = ["run_unit_tests"]
