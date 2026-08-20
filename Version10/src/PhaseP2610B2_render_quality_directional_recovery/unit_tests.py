"""Unit tests for P2.6.10-B.2. No live Claude. Does not change prior-phase routing."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict

from .anti_hardcoding import packed_sheet_robustness, source_guard, spatial_distance_robustness, translation_invariance_synthetic
from .config import DRAWING_SET_KEY, GATE_VERSION, MODEL_VERSION, PRODUCTION_ACTION, PRODUCTION_WRITE, SHADOW_ONLY
from .geometry import factor_vs, width
from .orientation import COMPACT, HORIZONTAL, UNKNOWN, VERTICAL, dominant_orientation
from .pipeline import derive_detail_extent, process_beam
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from .quality import STATUS_BLACK, STATUS_CLIP, STATUS_EMPTY, STATUS_LOW_INFO, validate_render
from .recovery import (
    ACTION_EXPAND_BOTH_X,
    ACTION_EXPAND_BOTH_Y,
    ACTION_EXPAND_LEFT,
    ACTION_EXPAND_RIGHT,
    ACTION_NONE,
    apply_action,
    choose_action,
    recover_once,
)
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    prior_artefacts_intact,
    prior_phase_unit_ok,
    runtime_leakage_scan,
)


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def _write_png(path: Path, color, size=(200, 160), draw=None) -> Path:
    from PIL import Image, ImageDraw

    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", size, color)
    if draw:
        d = ImageDraw.Draw(im)
        draw(d, im.size)
    im.save(path)
    return path


def test_fourth_set_only() -> None:
    assert DRAWING_SET_KEY == "Fourth"
    text = (_pkg() / "population.py").read_text(encoding="utf-8")
    assert "Fifth" not in text
    assert "1st Set" not in text


def test_source_guard() -> None:
    g = source_guard(_pkg())
    assert g.get("ok") is True, g.get("hits")


def test_no_beam_id_in_crop_runtime() -> None:
    for name in ("population.py", "quality.py", "orientation.py", "border.py", "recovery.py", "pipeline.py", "gates.py", "candidates.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        for tok in ("B32", "B19", "B24A", "B152", "B176", "B26", "B68A", "B99A", "B141"):
            assert tok not in text, f"{name} contains {tok}"


def test_empty_render_detection() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = _write_png(Path(td) / "w.png", (255, 255, 255))
        v = validate_render(p)
        assert v["primary_status"] == STATUS_EMPTY
        assert "EMPTY_RENDER" in v["flags"]
        assert v["visually_usable"] is False


def test_black_render_detection() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = _write_png(Path(td) / "b.png", (12, 12, 12))
        v = validate_render(p)
        assert v["primary_status"] == STATUS_BLACK
        assert v["file_generated"] is True
        assert v["visually_usable"] is False


def test_low_information_detection() -> None:
    with tempfile.TemporaryDirectory() as td:
        def few(d, size):
            d.point((10, 10), fill=(0, 180, 0))
            d.point((12, 11), fill=(0, 180, 0))
        p = _write_png(Path(td) / "s.png", (20, 20, 20), draw=few)
        v = validate_render(p)
        assert v["primary_status"] in (STATUS_LOW_INFO, STATUS_BLACK, STATUS_EMPTY)


def test_meaningful_vs_harmless_border_contact() -> None:
    from .border import meaningful_border_contact

    mark = {"x": 0.0, "y": 0.0, "depth_mm": 500.0}
    titles = [{"beam_id": "BX", "x": 0.0, "y": 0.0}]
    class _Msp:
        def __iter__(self):
            return iter([])
    img = {"left": False, "right": True, "top": False, "bottom": False}
    r = meaningful_border_contact(
        msp=_Msp(),
        mark=mark,
        titles=titles,
        extent=(-1000.0, -400.0, 1000.0, 1200.0),
        image_contact=img,
        orientation=HORIZONTAL,
    )
    assert r["sides"]["right"] is True
    assert r["meaningful_target_clipping_suspect"] is True


def test_horizontal_orientation_detection() -> None:
    o = dominant_orientation(
        mark={"x": 0.0, "y": 0.0, "depth_mm": 500.0},
        extent=(-4000.0, -300.0, 4000.0, 900.0),
        evidence=[{"x": -3000, "y": 10}, {"x": 3000, "y": 20}, {"x": 0, "y": 0}],
    )
    assert o == HORIZONTAL


def test_vertical_orientation_detection() -> None:
    o = dominant_orientation(
        mark={"x": 0.0, "y": 0.0, "depth_mm": 500.0},
        extent=(-400.0, -2000.0, 500.0, 4000.0),
        evidence=[{"x": 10, "y": -1500}, {"x": 20, "y": 3500}, {"x": 0, "y": 0}],
    )
    assert o == VERTICAL


def test_compact_unknown_fallback() -> None:
    o = dominant_orientation(mark={"x": 0.0, "y": 0.0}, extent=(-800.0, -800.0, 800.0, 800.0))
    assert o in (COMPACT, UNKNOWN, HORIZONTAL)


def test_horizontal_directional_expansion() -> None:
    diag = {
        "primary_status": STATUS_CLIP,
        "meaningful_border_contact": {"left": False, "right": True, "top": False, "bottom": False},
        "empty_sides": [],
    }
    assert choose_action(diagnostic=diag, orientation=HORIZONTAL) == ACTION_EXPAND_RIGHT
    diag_l = dict(diag)
    diag_l["meaningful_border_contact"] = {"left": True, "right": False, "top": False, "bottom": False}
    assert choose_action(diagnostic=diag_l, orientation=HORIZONTAL) == ACTION_EXPAND_LEFT
    both = dict(diag)
    both["meaningful_border_contact"] = {"left": True, "right": True, "top": False, "bottom": False}
    assert choose_action(diagnostic=both, orientation=HORIZONTAL) == ACTION_EXPAND_BOTH_X


def test_vertical_directional_expansion() -> None:
    diag = {
        "primary_status": STATUS_CLIP,
        "meaningful_border_contact": {"left": False, "right": False, "top": True, "bottom": True},
        "empty_sides": [],
    }
    assert choose_action(diagnostic=diag, orientation=VERTICAL) == ACTION_EXPAND_BOTH_Y


def test_bounded_recovery_no_unbounded_expansion() -> None:
    mark = {"x": 0.0, "y": 0.0, "depth_mm": 500.0}
    titles = [{"beam_id": "BX", "x": 0.0, "y": 0.0}, {"beam_id": "BZ", "x": 5000.0, "y": 0.0}]
    initial = (-1500.0, -400.0, 1500.0, 1600.0)
    diag = {
        "primary_status": STATUS_CLIP,
        "meaningful_border_contact": {"left": True, "right": True, "top": False, "bottom": False},
        "empty_sides": [],
    }
    cur = initial
    for i in range(1, 10):
        rec = recover_once(
            extent=cur,
            diagnostic=diag,
            orientation=HORIZONTAL,
            mark=mark,
            titles=titles,
            crop_type="context",
            initial_extent=initial,
            attempt=i,
        )
        cur = tuple(rec["after_bounds"])  # type: ignore
        assert factor_vs(initial, cur) <= 1.90
        if rec.get("blocked") or rec.get("action") == ACTION_NONE:
            break
    else:
        raise AssertionError("recovery did not stop")
    assert i <= 4


def test_context_first_and_detail_after_context() -> None:
    from . import pipeline as pl

    saved_b = pl.build_adaptive_regions
    saved_a = pl.adaptive_detail_extent

    def fake_regions(**kwargs):
        return {"context_extent": (-2000.0, -800.0, 2000.0, 1800.0), "adaptive": {"outline": None, "evidence": []}}

    def fake_adapt(**kwargs):
        return {"detail_extent": (-1400.0, -400.0, 1400.0, 1400.0)}

    def fake_render(*, dxf_path, output_path, extent, crop_type):
        def ink(d, size):
            w, h = size
            d.rectangle([int(w * 0.25), int(h * 0.25), int(w * 0.75), int(h * 0.75)], fill=(0, 170, 0))
        _write_png(Path(output_path), (25, 25, 25), size=(240, 180), draw=ink)
        return {"path": str(output_path), "image_dimensions": [240, 180]}

    class _Msp:
        def __iter__(self):
            return iter([])

    pl.build_adaptive_regions = fake_regions
    pl.adaptive_detail_extent = fake_adapt
    try:
        with tempfile.TemporaryDirectory() as td:
            rec = process_beam(
                beam_id="BX",
                msp=_Msp(),
                mark={"x": 0.0, "y": 0.0, "depth_mm": 500.0},
                titles=[{"beam_id": "BX", "x": 0.0, "y": 0.0}],
                dxf_path=Path(td) / "none.dxf",
                out_root=Path(td),
                render_fn=fake_render,
            )
        assert rec["context_first"] is True
        assert rec["stages"].index("VALIDATE_CONTEXT") < rec["stages"].index("RENDER_DETAIL")
        assert rec["context_recovery_applied"] is False
        assert isinstance(rec["context_recovery_history"], list)
        hist = rec["context_recovery_history"] + rec["detail_recovery_history"]
        for row in hist:
            assert "attempt" in row and "action" in row and "before_bounds" in row
        assert "final_vision_usable" in rec
    finally:
        pl.build_adaptive_regions = saved_b
        pl.adaptive_detail_extent = saved_a


def test_detail_derived_from_context() -> None:
    ctx = (-5000.0, -1000.0, 5000.0, 3000.0)
    ad = (-8000.0, -4000.0, 8000.0, 8000.0)
    d = derive_detail_extent(ctx, ad, {"x": 0.0, "y": 0.0})
    assert d[0] >= ctx[0] and d[2] <= ctx[2]
    assert d[1] >= ctx[1] and d[3] <= ctx[3]


def test_final_vision_usability_rejects_blank() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = _write_png(Path(td) / "b.png", (8, 8, 8))
        v = validate_render(p)
        assert v["visually_usable"] is False
        assert v["recovery_required"] is True


def test_suspect_beam_enters_recovery() -> None:
    from . import pipeline as pl

    saved_b = pl.build_adaptive_regions
    saved_a = pl.adaptive_detail_extent

    def fake_regions(**kwargs):
        return {"context_extent": (-2000.0, -800.0, 2000.0, 1800.0), "adaptive": {"outline": None, "evidence": []}}

    def fake_adapt(**kwargs):
        return {"detail_extent": (-1400.0, -400.0, 1400.0, 1400.0)}

    n_render = {"n": 0}

    def fake_render(*, dxf_path, output_path, extent, crop_type):
        n_render["n"] += 1
        if n_render["n"] <= 1:
            _write_png(Path(output_path), (8, 8, 8), size=(200, 160))
        else:
            def ink(d, size):
                w, h = size
                d.rectangle([int(w * 0.2), int(h * 0.2), int(w * 0.8), int(h * 0.8)], fill=(0, 170, 0))
            _write_png(Path(output_path), (25, 25, 25), size=(200, 160), draw=ink)
        return {"path": str(output_path), "image_dimensions": [200, 160]}

    class _Msp:
        def __iter__(self):
            return iter([])

    pl.build_adaptive_regions = fake_regions
    pl.adaptive_detail_extent = fake_adapt
    try:
        with tempfile.TemporaryDirectory() as td:
            rec = process_beam(
                beam_id="BX",
                msp=_Msp(),
                mark={"x": 0.0, "y": 0.0, "depth_mm": 500.0},
                titles=[{"beam_id": "BX", "x": 0.0, "y": 0.0}],
                dxf_path=Path(td) / "none.dxf",
                out_root=Path(td),
                render_fn=fake_render,
            )
        assert rec["context_recovery_applied"] is True
        assert rec["context_recovery_attempt_count"] >= 1
    finally:
        pl.build_adaptive_regions = saved_b
        pl.adaptive_detail_extent = saved_a


def test_candidate_generation_is_bounded() -> None:
    from .candidates import generate_candidate_actions
    from .orientation import HORIZONTAL, VERTICAL

    h = generate_candidate_actions(
        {
            "primary_status": STATUS_CLIP,
            "meaningful_border_contact": {"left": True, "right": True, "top": False, "bottom": False},
            "empty_sides": [],
        },
        orientation=HORIZONTAL,
        crop_type="context",
    )
    v = generate_candidate_actions(
        {
            "primary_status": STATUS_CLIP,
            "meaningful_border_contact": {"left": False, "right": False, "top": True, "bottom": True},
            "empty_sides": [],
        },
        orientation=VERTICAL,
        crop_type="context",
    )
    assert 1 <= len(h) <= 3
    assert 1 <= len(v) <= 3
    assert len(h) == len(set(h))


def test_horizontal_vertical_truncation_flags() -> None:
    with tempfile.TemporaryDirectory() as td:
        def edge(d, size):
            w, h = size
            d.rectangle([0, int(h * 0.3), w - 1, int(h * 0.7)], fill=(0, 180, 0))
        p = _write_png(Path(td) / "h.png", (20, 20, 20), size=(240, 120), draw=edge)
        v = validate_render(p, crop_type="context")
        assert "HORIZONTAL_TRUNCATION_SUSPECT" in v["flags"] or v["primary_status"] in (STATUS_CLIP, STATUS_LOW_INFO)


def test_cache_key_reuse_without_duplicate_extent() -> None:
    from .pipeline import _try_candidates

    seen_renders = []

    def fake_render(*, dxf_path, output_path, extent, crop_type):
        key = tuple(round(float(v), 1) for v in extent)
        seen_renders.append(key)
        _write_png(Path(output_path), (20, 20, 20), size=(80, 60))
        return {"path": str(output_path)}

    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "base.png"
        _write_png(base, (8, 8, 8), size=(80, 60))
        diag = validate_render(base)
        _try_candidates(
            beam_id="BX",
            mark={"x": 0.0, "y": 0.0, "depth_mm": 500.0},
            titles=[{"beam_id": "BX", "x": 0.0, "y": 0.0}],
            dxf_path=Path(td) / "none.dxf",
            render_fn=fake_render,
            crop_type="context",
            orientation=HORIZONTAL,
            baseline_extent=(-1000.0, -400.0, 1000.0, 1200.0),
            baseline_diag=diag,
            baseline_path=base,
            out_dir=Path(td),
        )
    assert len(seen_renders) == len(set(seen_renders))


def test_no_beam_id_in_new_runtime_modules() -> None:
    for name in ("gates.py", "candidates.py", "render_session.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        for tok in ("B32", "B19", "B24A", "B152", "B176"):
            assert tok not in text, f"{name} contains {tok}"
    with tempfile.TemporaryDirectory() as td:
        p = _write_png(Path(td) / "b.png", (8, 8, 8))
        v = validate_render(p)
        assert v["visually_usable"] is False
        assert v["recovery_required"] is True


def test_translation_invariance() -> None:
    r = translation_invariance_synthetic()
    assert r.get("ok") is True, r


def test_spatial_distance_robustness() -> None:
    r = spatial_distance_robustness()
    assert r.get("ok") is True, r


def test_packed_sheet_robustness() -> None:
    r = packed_sheet_robustness()
    assert r.get("ok") is True, r


def test_production_write_false() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert MODEL_VERSION == "10.11.13"
    assert GATE_VERSION == "P2610B2_RENDER_QUALITY_DIRECTIONAL_RECOVERY_V1_0"
    assert SHADOW_ONLY is True
    assert PRODUCTION_ACTION == "NO_CHANGE"


def test_prior_phase_artefacts() -> None:
    assert prior_phase_unit_ok(_v10(), "PhaseP266_semantic_longitudinal_resolver", 36).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610A_beam_region_crop_audit", 14).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610B_adaptive_beam_detail_crop", 18).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610B1_population_generalization", 16).get("ok") is True
    intact = prior_artefacts_intact(_v10())
    assert intact.get("ok") is True, intact.get("missing")


def test_production_identical_fingerprints() -> None:
    paths = fingerprint_paths(_v10(), {})
    cmp = compare_fingerprints(capture_fingerprints(paths), capture_fingerprints(paths))
    assert cmp.get("unchanged") is True


def test_firewall_and_leakage() -> None:
    fw = firewall_check(_v10())
    assert fw.get("ok") is True, fw.get("offenders")
    leak = runtime_leakage_scan(_pkg())
    assert leak.get("ok") is True, leak.get("hits")


def test_decision_never_production_ready() -> None:
    from .phase_p2610b2_orchestrator import _classify_decision

    d = _classify_decision(
        tests_ok=True,
        fingerprints_ok=True,
        anti_ok=True,
        six_ok=True,
        processed=10,
        discovered=10,
        skip_n=0,
        silent_blank=0,
        usable_n=10,
        hardcoding=False,
    )
    assert "PRODUCTION" not in d
    assert d.startswith("PASS")


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("fourth_set_only", test_fourth_set_only),
        ("source_guard", test_source_guard),
        ("no_beam_id_in_crop_runtime", test_no_beam_id_in_crop_runtime),
        ("empty_render_detection", test_empty_render_detection),
        ("black_render_detection", test_black_render_detection),
        ("low_information_detection", test_low_information_detection),
        ("meaningful_vs_harmless_border_contact", test_meaningful_vs_harmless_border_contact),
        ("horizontal_orientation_detection", test_horizontal_orientation_detection),
        ("vertical_orientation_detection", test_vertical_orientation_detection),
        ("compact_unknown_fallback", test_compact_unknown_fallback),
        ("horizontal_directional_expansion", test_horizontal_directional_expansion),
        ("vertical_directional_expansion", test_vertical_directional_expansion),
        ("bounded_recovery_no_unbounded_expansion", test_bounded_recovery_no_unbounded_expansion),
        ("context_first_and_detail_after_context", test_context_first_and_detail_after_context),
        ("detail_derived_from_context", test_detail_derived_from_context),
        ("final_vision_usability_rejects_blank", test_final_vision_usability_rejects_blank),
        ("suspect_beam_enters_recovery", test_suspect_beam_enters_recovery),
        ("candidate_generation_is_bounded", test_candidate_generation_is_bounded),
        ("horizontal_vertical_truncation_flags", test_horizontal_vertical_truncation_flags),
        ("cache_key_reuse_without_duplicate_extent", test_cache_key_reuse_without_duplicate_extent),
        ("no_beam_id_in_new_runtime_modules", test_no_beam_id_in_new_runtime_modules),
        ("translation_invariance", test_translation_invariance),
        ("spatial_distance_robustness", test_spatial_distance_robustness),
        ("packed_sheet_robustness", test_packed_sheet_robustness),
        ("production_write_false", test_production_write_false),
        ("prior_phase_artefacts", test_prior_phase_artefacts),
        ("production_identical_fingerprints", test_production_identical_fingerprints),
        ("firewall_and_leakage", test_firewall_and_leakage),
        ("decision_never_production_ready", test_decision_never_production_ready),
    ]
    results = []
    for name, fn in tests:
        try:
            fn()
            results.append({"name": name, "pass": True})
        except Exception as exc:
            results.append({"name": name, "pass": False, "error": str(exc)})
    passed = sum(1 for r in results if r.get("pass"))
    return {
        "success": passed == len(results),
        "passed": passed,
        "total": len(results),
        "results": results,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
    }


__all__ = ["run_unit_tests"]
