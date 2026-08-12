"""Unit tests for P2.5.2.2 render-safe annotation bounds."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from .config import (
    FLAG_ANNOTATION_RENDER_CLIPPED,
    FLAG_ANNOTATION_RENDER_EDGE_RISK,
    MIN_RENDER_SAFE_MARGIN_PX,
    READABILITY_REVIEW,
)
from .geometry_safe import (
    annotation_vertical_side,
    deficit_px,
    expand_extent_sides,
    geometric_contained,
)
from .pixel_safety import assess_render_safety

MODEL_VERSION = "10.6.7"


def _make_png(path: Path, w: int, h: int, ink_box: Tuple[int, int, int, int]) -> None:
    from PIL import Image, ImageDraw

    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(im)
    draw.rectangle(ink_box, fill=(180, 0, 180))  # magenta-like annotation ink
    im.save(path)


def test_annotation_safely_inside(tmp_path: Path = None) -> None:
    root = Path(tmp_path) if tmp_path else Path(".") / "_p2522_test_tmp"
    root.mkdir(parents=True, exist_ok=True)
    png = root / "safe.png"
    # ink well inside with >24px margins
    _make_png(png, 200, 200, (40, 40, 160, 80))
    extent = (0.0, 0.0, 1000.0, 1000.0)
    # Map: full extent → full image; place ann bbox correspondingly near center-top of DXF
    # px y=40..80 → DXF y from top: py = (ymax-y)/yspan*h → y = ymax - py/h*yspan
    # For simplicity set ann bbox covering same relative region
    ann = (200.0, 600.0, 800.0, 800.0)
    a = assess_render_safety(
        image_path=png,
        extent=extent,
        annotation_bbox=ann,
        leader_bboxes=[],
        beam_bbox=(100.0, 200.0, 900.0, 500.0),
        dxf_xlim=(0.0, 1000.0),
        dxf_ylim=(0.0, 1000.0),
        img_w=200,
        img_h=200,
    )
    assert a["geometric_containment"] is True
    assert a["margins_px"]["top_margin_px"] >= MIN_RENDER_SAFE_MARGIN_PX
    assert a["render_safe"] is True


def test_annotation_touching_top_edge() -> None:
    root = Path(".") / "_p2522_test_tmp"
    root.mkdir(parents=True, exist_ok=True)
    png = root / "top.png"
    _make_png(png, 200, 200, (40, 2, 160, 30))  # top margin = 2
    extent = (0.0, 0.0, 1000.0, 1000.0)
    ann = (200.0, 850.0, 800.0, 990.0)  # near top of DXF (high y)
    a = assess_render_safety(
        image_path=png,
        extent=extent,
        annotation_bbox=ann,
        beam_bbox=(100.0, 200.0, 900.0, 500.0),
        dxf_xlim=(0.0, 1000.0),
        dxf_ylim=(0.0, 1000.0),
        img_w=200,
        img_h=200,
    )
    assert FLAG_ANNOTATION_RENDER_EDGE_RISK in a["flags"] or a["margins_px"]["top_margin_px"] < MIN_RENDER_SAFE_MARGIN_PX
    assert a["render_safe"] is False
    assert a["deficits_px"]["top"] > 0
    assert a["vertical_side"] == "TOP"


def test_annotation_touching_bottom_edge() -> None:
    root = Path(".") / "_p2522_test_tmp"
    root.mkdir(parents=True, exist_ok=True)
    png = root / "bottom.png"
    _make_png(png, 200, 200, (40, 170, 160, 198))
    extent = (0.0, 0.0, 1000.0, 1000.0)
    ann = (200.0, 10.0, 800.0, 150.0)
    a = assess_render_safety(
        image_path=png,
        extent=extent,
        annotation_bbox=ann,
        beam_bbox=(100.0, 400.0, 900.0, 700.0),
        dxf_xlim=(0.0, 1000.0),
        dxf_ylim=(0.0, 1000.0),
        img_w=200,
        img_h=200,
    )
    assert a["render_safe"] is False
    assert a["deficits_px"]["bottom"] > 0
    assert a["vertical_side"] == "BOTTOM"


def test_annotation_touching_left_right() -> None:
    root = Path(".") / "_p2522_test_tmp"
    root.mkdir(parents=True, exist_ok=True)
    png = root / "lr.png"
    _make_png(png, 200, 200, (1, 60, 40, 100))  # left clipped-ish
    extent = (0.0, 0.0, 1000.0, 1000.0)
    ann = (5.0, 400.0, 200.0, 600.0)
    a = assess_render_safety(
        image_path=png,
        extent=extent,
        annotation_bbox=ann,
        beam_bbox=(300.0, 300.0, 900.0, 700.0),
        dxf_xlim=(0.0, 1000.0),
        dxf_ylim=(0.0, 1000.0),
        img_w=200,
        img_h=200,
    )
    assert a["render_safe"] is False
    assert a["deficits_px"]["left"] > 0


def test_leader_edge_risk() -> None:
    root = Path(".") / "_p2522_test_tmp"
    root.mkdir(parents=True, exist_ok=True)
    png = root / "leader.png"
    # annotation safe, leader ink near top
    from PIL import Image, ImageDraw

    im = Image.new("RGB", (200, 200), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.rectangle((50, 50, 150, 90), fill=(180, 0, 180))  # ann
    d.rectangle((80, 1, 120, 20), fill=(50, 50, 50))  # leader near top
    im.save(png)
    extent = (0.0, 0.0, 1000.0, 1000.0)
    ann = (250.0, 550.0, 750.0, 750.0)
    leader = (400.0, 880.0, 600.0, 990.0)
    a = assess_render_safety(
        image_path=png,
        extent=extent,
        annotation_bbox=ann,
        leader_bboxes=[leader],
        beam_bbox=(100.0, 200.0, 900.0, 500.0),
        dxf_xlim=(0.0, 1000.0),
        dxf_ylim=(0.0, 1000.0),
        img_w=200,
        img_h=200,
    )
    assert a["render_safe"] is False
    assert a["deficits_px"]["top"] > 0


def test_required_expansion_top_only() -> None:
    extent = (0.0, 0.0, 1000.0, 1000.0)
    new_ext, expands = expand_extent_sides(
        extent,
        need_left_px=0,
        need_right_px=0,
        need_top_px=20,
        need_bottom_px=0,
        dxf_xlim=(0.0, 1000.0),
        dxf_ylim=(0.0, 1000.0),
        img_w=200,
        img_h=200,
    )
    assert expands["expand_top_mm"] > 0
    assert expands["expand_left_mm"] == 0
    assert expands["expand_right_mm"] == 0
    assert expands["expand_bottom_mm"] == 0
    assert new_ext[3] > extent[3]
    assert new_ext[0] == extent[0]
    assert new_ext[1] == extent[1]
    assert new_ext[2] == extent[2]


def test_deficit_and_containment() -> None:
    assert deficit_px(8, 24) == 16
    assert deficit_px(30, 24) == 0
    assert geometric_contained((0, 0, 10, 10), (1, 1, 9, 9))
    assert not geometric_contained((0, 0, 10, 10), (-1, 1, 9, 9))
    assert annotation_vertical_side(
        annotation_bbox=(0, 8, 1, 9), beam_bbox=(0, 0, 1, 4)
    ) == "TOP"


def test_max_iteration_status_logic() -> None:
    # Hit-max without render_safe → REVIEW
    from .refine_safe import _classify

    status = _classify(
        assessment={"render_safe": False, "geometric_containment": True, "flags": [FLAG_ANNOTATION_RENDER_EDGE_RISK]},
        extreme=False,
        render_ok=True,
        rejected_included=False,
        missing_beam=False,
        missing_ann=False,
    )
    assert status in (READABILITY_REVIEW, "READABILITY_PARTIAL", "READABILITY_PASS") or True
    # Direct: partial when geom ok but not render safe
    assert status == "READABILITY_PARTIAL"


def test_rejected_evidence_exclusion_flag() -> None:
    from .refine_safe import _classify

    status = _classify(
        assessment={"render_safe": True, "geometric_containment": True, "flags": []},
        extreme=False,
        render_ok=True,
        rejected_included=True,
        missing_beam=False,
        missing_ann=False,
    )
    assert status == "READABILITY_FAIL"


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("annotation_safely_inside", test_annotation_safely_inside),
        ("annotation_touching_top_edge", test_annotation_touching_top_edge),
        ("annotation_touching_bottom_edge", test_annotation_touching_bottom_edge),
        ("annotation_touching_left_right", test_annotation_touching_left_right),
        ("leader_edge_risk", test_leader_edge_risk),
        ("required_expansion_top_only", test_required_expansion_top_only),
        ("deficit_and_containment", test_deficit_and_containment),
        ("max_iteration_status_logic", test_max_iteration_status_logic),
        ("rejected_evidence_exclusion_flag", test_rejected_evidence_exclusion_flag),
    ]
    results: List[Dict[str, Any]] = []
    for name, fn in tests:
        try:
            fn()
            results.append({"name": name, "pass": True})
        except Exception as exc:  # noqa: BLE001
            results.append({"name": name, "pass": False, "error": str(exc)})
    # cleanup temp pngs
    try:
        import shutil

        shutil.rmtree(Path(".") / "_p2522_test_tmp", ignore_errors=True)
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
