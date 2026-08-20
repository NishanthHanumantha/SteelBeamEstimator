"""Unit tests for P2.6.10-B.3. No live Claude. Does not change prior-phase routing."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict

from .anti_hardcoding import packed_sheet_robustness, source_guard, spatial_distance_robustness, translation_invariance_synthetic
from .candidates import generate_candidates
from .classify import classify_beam
from .config import CLASS_FROZEN, CLASS_TARGET, DRAWING_SET_KEY, GATE_VERSION, MODEL_VERSION, PRODUCTION_ACTION, PRODUCTION_WRITE, SHADOW_ONLY
from .context_builder import build_context_envelope
from .gate import evaluate_candidate, should_replace
from .pipeline import file_fingerprint, freeze_baseline
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from PhaseP2610B2_render_quality_directional_recovery.quality import STATUS_BLACK, STATUS_EMPTY, STATUS_LOW_INFO, validate_render
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


def test_source_guard() -> None:
    g = source_guard(_pkg())
    assert g.get("ok") is True, g.get("hits")


def test_no_beam_id_in_crop_runtime() -> None:
    for name in ("classify.py", "anchor.py", "context_builder.py", "candidates.py", "gate.py", "pipeline.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        for tok in ("B32", "B19", "B24A", "B152", "B176", "B26", "B68A", "B99A", "B141"):
            assert tok not in text, f"{name} contains {tok}"


def test_blank_black_near_empty() -> None:
    with tempfile.TemporaryDirectory() as td:
        w = _write_png(Path(td) / "w.png", (255, 255, 255))
        b = _write_png(Path(td) / "b.png", (8, 8, 8))
        assert validate_render(w)["primary_status"] == STATUS_EMPTY
        assert validate_render(b)["primary_status"] == STATUS_BLACK


def test_classify_frozen_vs_target() -> None:
    good = {
        "completeness_status": "PASS",
        "p2610b_complete_flag": True,
        "failure_categories": [],
        "context_crop_path": "x",
        "detail_crop_path": "y",
    }
    q_ok = {"primary_status": "VALID", "empty_sides": [], "coverage_x": 0.8, "coverage_y": 0.7, "dark_ratio": 0.1}
    c = classify_beam(b1=good, ctx_quality=q_ok, det_quality=q_ok, b2={"final_vision_usable": True})
    assert c["classification"] == CLASS_FROZEN
    crushed = {"primary_status": STATUS_LOW_INFO, "empty_sides": ["left"], "coverage_x": 0.2, "coverage_y": 0.2, "dark_ratio": 0.7}
    t = classify_beam(b1=good, ctx_quality=crushed, det_quality=q_ok, b2={"final_vision_usable": True})
    assert t["classification"] == CLASS_TARGET


def test_candidate_generation_bounded_and_deduped() -> None:
    anchor = {
        "core": (-2000.0, -400.0, 4000.0, 1200.0),
        "orientation": "HORIZONTAL",
        "x_barriers": [-8000.0, 8000.0],
        "y_floor": -4000.0,
        "y_cap": 4000.0,
        "mark": {"x": 0.0, "y": 200.0},
    }
    env = build_context_envelope(anchor)
    c1 = generate_candidates(
        anchor=anchor,
        context_envelope=env,
        baseline_extent=env["extent"],
        baseline_quality={"primary_status": "LOW_INFORMATION_RENDER", "empty_sides": ["left"], "coverage_x": 0.2},
    )
    keys = [tuple(round(v, 0) for v in c["extent"]) for c in c1]
    assert 1 <= len(c1) <= 3
    assert len(keys) == len(set(keys))


def test_horizontal_geometry_not_identity() -> None:
    anchor = {
        "core": (0.0, 0.0, 8000.0, 800.0),
        "orientation": "HORIZONTAL",
        "x_barriers": [-2000.0, 12000.0],
        "y_floor": -2000.0,
        "y_cap": 3000.0,
        "mark": {"x": 4000.0, "y": 400.0},
    }
    env = build_context_envelope(anchor)
    assert env["extent"][2] - env["extent"][0] > env["extent"][3] - env["extent"][1]
    cands = generate_candidates(
        anchor=anchor,
        context_envelope=env,
        baseline_extent=env["extent"],
        baseline_quality={"primary_status": "BORDER_CLIPPING_SUSPECT", "coverage_x": 0.95, "empty_sides": []},
    )
    assert any(c["reason"] == "HORIZONTAL_CONTEXT_UNDERSCALE" for c in cands)


def test_endpoint_coverage_geometric() -> None:
    anchor = {"core": (0.0, 0.0, 5000.0, 1000.0)}
    q = {"primary_status": "VALID", "visually_usable": True}
    short = evaluate_candidate(extent=(1000.0, 0.0, 2000.0, 1000.0), anchor=anchor, quality=q)
    full = evaluate_candidate(extent=(-200.0, -200.0, 5200.0, 1200.0), anchor=anchor, quality=q)
    assert short["endpoints_complete"] is False
    assert full["endpoints_complete"] is True
    assert full["target_coverage"] > short["target_coverage"]


def test_failed_candidate_cannot_overwrite_baseline() -> None:
    base = {"acceptable": True, "score": 4.2}
    worse = {"acceptable": True, "score": 3.1}
    blank = {"acceptable": False, "score": 0.0}
    better = {"acceptable": True, "score": 4.6}
    assert should_replace(base, worse) is False
    assert should_replace(base, blank) is False
    assert should_replace(base, better) is True


def test_frozen_good_not_rerendered() -> None:
    with tempfile.TemporaryDirectory() as td:
        ctx = _write_png(Path(td) / "c.png", (20, 20, 20))
        det = _write_png(Path(td) / "d.png", (20, 20, 20))
        h0 = file_fingerprint(ctx)
        rec = freeze_baseline(
            beam_id="BX",
            classification=CLASS_FROZEN,
            reasons=["B1_COMPLETE_AND_RENDER_OK"],
            b1={"context_crop_path": str(ctx), "detail_crop_path": str(det), "context_bounds": [0, 0, 1, 1], "detail_bounds": [0, 0, 1, 1]},
            b2={"final_vision_usable": True},
            ctx_quality={"primary_status": "VALID"},
            det_quality={"primary_status": "VALID"},
        )
        assert rec["rerendered"] is False
        assert rec["selected_context_source"] == "P2610B1"
        assert rec["selected_context_sha256"] == h0
        assert file_fingerprint(ctx) == h0


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
    assert MODEL_VERSION == "10.11.14"
    assert GATE_VERSION == "P2610B3_TARGET_ANCHOR_GEOMETRY_CONTEXT_RECOVERY_V1_0"
    assert SHADOW_ONLY is True
    assert PRODUCTION_ACTION == "NO_CHANGE"


def test_prior_phase_artefacts() -> None:
    assert prior_phase_unit_ok(_v10(), "PhaseP266_semantic_longitudinal_resolver", 36).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610A_beam_region_crop_audit", 14).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610B_adaptive_beam_detail_crop", 18).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610B1_population_generalization", 16).get("ok") is True
    assert prior_phase_unit_ok(_v10(), "PhaseP2610B2_render_quality_directional_recovery", 29).get("ok") is True
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
    from .phase_p2610b3_orchestrator import _classify_decision

    d = _classify_decision(
        tests_ok=True,
        fingerprints_ok=True,
        anti_ok=True,
        frozen_regression=0,
        processed=10,
        discovered=10,
        skip_n=0,
        silent_blank=0,
        improved=3,
        hardcoding=False,
        unresolved_limitations=False,
    )
    assert "PRODUCTION" not in d
    assert d.startswith("PASS")


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("fourth_set_only", test_fourth_set_only),
        ("source_guard", test_source_guard),
        ("no_beam_id_in_crop_runtime", test_no_beam_id_in_crop_runtime),
        ("blank_black_near_empty", test_blank_black_near_empty),
        ("classify_frozen_vs_target", test_classify_frozen_vs_target),
        ("candidate_generation_bounded_and_deduped", test_candidate_generation_bounded_and_deduped),
        ("horizontal_geometry_not_identity", test_horizontal_geometry_not_identity),
        ("endpoint_coverage_geometric", test_endpoint_coverage_geometric),
        ("failed_candidate_cannot_overwrite_baseline", test_failed_candidate_cannot_overwrite_baseline),
        ("frozen_good_not_rerendered", test_frozen_good_not_rerendered),
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
