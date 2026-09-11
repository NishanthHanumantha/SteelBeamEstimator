"""Unit tests for P2.6.10-B. No live Claude. Does not change P2.6.6–P2.6.10-A routing."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .completeness import evaluate_completeness
from .config import GATE_VERSION, MODEL_VERSION, PRODUCTION_ACTION, PRODUCTION_WRITE, SHADOW_ONLY
from .evaluator import classify_phase
from .evidence import classify_text, next_row_y_cap, owned_by_mark, prev_row_y_floor, x_barriers
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    prior_phase_unit_ok,
    runtime_leakage_scan,
)


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def test_title_anchor_and_text_kinds() -> None:
    assert classify_text("5-Y20") == "REINF"
    assert classify_text("4L-Y8@100C/C") == "STIRRUP"
    assert classify_text("1400") == "DIM"
    assert classify_text("NOTES") == "OTHER"


def test_adaptive_upward_expansion_keeps_top_band() -> None:
    mark = {"x": 0.0, "y": 0.0, "depth_mm": 500.0}
    titles = [
        {"beam_id": "BX", "x": 0.0, "y": 0.0},
        {"beam_id": "BY", "x": 100.0, "y": 3300.0},
    ]
    cap = next_row_y_cap(mark, titles)
    assert cap > 1971.0
    assert cap < 3300.0
    tight = next_row_y_cap(
        {"x": 0.0, "y": 0.0, "depth_mm": 600.0},
        [{"beam_id": "BX", "x": 0.0, "y": 0.0}, {"beam_id": "BY", "x": 80.0, "y": 2072.0}],
    )
    assert tight > 1716.0
    assert tight < 2072.0
    deep = {"x": 0.0, "y": 0.0, "depth_mm": 1100.0}
    deep_titles = [
        {"beam_id": "BX", "x": 0.0, "y": 0.0},
        {"beam_id": "BY", "x": 80.0, "y": 3300.0},
    ]
    deep_cap = next_row_y_cap(deep, deep_titles)
    assert deep_cap > 2444.0
    assert deep_cap < 3300.0
    assert prev_row_y_floor(mark, [{"beam_id": "BZ", "x": 0.0, "y": -2800.0}]) > -2800.0


def test_adaptive_horizontal_expansion_keeps_right_extra() -> None:
    mark = {"x": 0.0, "y": 0.0, "depth_mm": 1100.0}
    titles = [
        {"beam_id": "BX", "x": 0.0, "y": 0.0},
        {"beam_id": "BZ", "x": 5000.0, "y": 50.0},
    ]
    left, right = x_barriers(mark, titles)
    assert right > 2450.0
    assert right < 5000.0
    assert left < -100.0


def test_top_and_bottom_evidence_detection() -> None:
    mark = {"x": 0.0, "y": 0.0, "depth_mm": 500.0}
    extent = (-2000.0, -400.0, 2000.0, 2200.0)
    evidence = [
        {"kind": "STIRRUP", "band": "STIRRUP_BAND", "x": 10.0, "y": 300.0, "dx": 10.0, "dy": 300.0, "text": "4L-Y8@100C/C"},
        {"kind": "REINF", "band": "BOTTOM_REINFORCEMENT_BAND", "x": 10.0, "y": 600.0, "dx": 10.0, "dy": 600.0, "text": "5-Y16"},
        {"kind": "REINF", "band": "TOP_REINFORCEMENT_BAND", "x": 10.0, "y": 1971.0, "dx": 10.0, "dy": 1971.0, "text": "5-Y20"},
    ]
    c = evaluate_completeness(
        beam_id="BX",
        extent=extent,
        mark=mark,
        outline=(-200.0, 800.0),
        evidence=evidence,
        titles=[{"beam_id": "BX", "x": 0.0, "y": 0.0}],
    )
    assert c["top_reinforcement_visible"] == "YES"
    assert c["bottom_reinforcement_visible"] == "YES"
    assert c["stirrup_visible"] == "YES"


def test_dimension_and_row_isolation() -> None:
    mark = {"x": 0.0, "y": 0.0}
    titles = [
        {"beam_id": "BX", "x": 0.0, "y": 0.0},
        {"beam_id": "BY", "x": 100.0, "y": 3500.0},
        {"beam_id": "BZ", "x": 4000.0, "y": 0.0},
    ]
    assert owned_by_mark(50.0, 1971.0, mark, titles) is True
    assert next_row_y_cap(mark, titles) < 3400.0
    assert owned_by_mark(3900.0, 50.0, mark, titles) is False
    assert classify_text("1400") == "DIM"


def test_no_r1_dependency() -> None:
    forbidden = (
        "annotations_by_beam",
        "reinforcement_annotations.json",
        "PhaseP266_",
        "PhaseP267_",
        "PhaseP268_",
        "PhaseP269_",
        "associate_annotations",
    )
    for name in ("evidence.py", "envelope.py", "completeness.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        for tok in forbidden:
            assert tok not in text, f"{name} contains {tok}"


def test_no_beam_id_hardcoding_in_runtime() -> None:
    for name in ("evidence.py", "envelope.py", "completeness.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        for token in ("B128", "B141", "B55", "B66", "B161", "B65"):
            assert token not in text, f"{name} contains {token}"


def test_no_gt_usage() -> None:
    for name in ("evidence.py", "envelope.py", "completeness.py", "evaluator.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "TRUE_RECOVERY" not in text
        assert "load_gt_universe" not in text
        assert "EstimatorOutput" not in text


def test_production_write_false() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert MODEL_VERSION == "10.11.11"
    assert GATE_VERSION == "P2610B_ADAPTIVE_BEAM_DETAIL_COMPLETENESS_V1_0"
    assert SHADOW_ONLY is True
    assert PRODUCTION_ACTION == "NO_CHANGE"


def test_p266_regression_file() -> None:
    assert prior_phase_unit_ok(_v10(), "PhaseP266_semantic_longitudinal_resolver", 36).get("ok") is True


def test_p267_regression_file() -> None:
    assert prior_phase_unit_ok(_v10(), "PhaseP267_live_semantic_arbitration", 31).get("ok") is True


def test_p268_regression_file() -> None:
    assert prior_phase_unit_ok(_v10(), "PhaseP268_evidence_conflict_arbitration", 27).get("ok") is True


def test_p269_regression_file() -> None:
    assert prior_phase_unit_ok(_v10(), "PhaseP269_reinforcement_group_interpretation", 20).get("ok") is True


def test_p2610a_artifact_preservation() -> None:
    info = prior_phase_unit_ok(_v10(), "PhaseP2610A_beam_region_crop_audit", 14)
    assert info.get("ok") is True
    status = _v10() / "data" / "output" / "PhaseP2610A_beam_region_crop_audit" / "P2.6.10-A_STATUS.md"
    assert status.exists()


def test_production_identical_fingerprints() -> None:
    paths = fingerprint_paths(_v10(), {})
    cmp = compare_fingerprints(capture_fingerprints(paths), capture_fingerprints(paths))
    assert cmp.get("unchanged") is True


def test_firewall_and_leakage() -> None:
    fw = firewall_check(_v10())
    assert fw.get("ok") is True, fw.get("offenders")
    leak = runtime_leakage_scan(_pkg())
    assert leak.get("ok") is True, leak.get("hits")


def test_classify_never_production_ready() -> None:
    rec = classify_phase(tests_ok=True, fingerprints_ok=True, six_beams=True, crops_complete=True, readiness="READY")
    assert rec["decision"] == "SAFE_SHADOW_BENCHMARK"
    assert "PRODUCTION_READY" not in rec["decision"]


def test_missing_top_is_incomplete() -> None:
    mark = {"x": 0.0, "y": 0.0, "depth_mm": 500.0}
    extent = (-2000.0, -400.0, 2000.0, 1600.0)
    evidence = [
        {"kind": "REINF", "band": "BOTTOM_REINFORCEMENT_BAND", "x": 10.0, "y": 600.0, "dx": 10.0, "dy": 600.0, "text": "5-Y16"},
        {"kind": "REINF", "band": "TOP_REINFORCEMENT_BAND", "x": 10.0, "y": 1971.0, "dx": 10.0, "dy": 1971.0, "text": "5-Y20"},
    ]
    c = evaluate_completeness(
        beam_id="BX",
        extent=extent,
        mark=mark,
        outline=(-200.0, 800.0),
        evidence=evidence,
        titles=[{"beam_id": "BX", "x": 0.0, "y": 0.0}],
    )
    assert c["top_reinforcement_visible"] == "NO"


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("title_anchor_and_text_kinds", test_title_anchor_and_text_kinds),
        ("adaptive_upward_expansion_keeps_top_band", test_adaptive_upward_expansion_keeps_top_band),
        ("adaptive_horizontal_expansion_keeps_right_extra", test_adaptive_horizontal_expansion_keeps_right_extra),
        ("top_and_bottom_evidence_detection", test_top_and_bottom_evidence_detection),
        ("dimension_and_row_isolation", test_dimension_and_row_isolation),
        ("no_r1_dependency", test_no_r1_dependency),
        ("no_beam_id_hardcoding_in_runtime", test_no_beam_id_hardcoding_in_runtime),
        ("no_gt_usage", test_no_gt_usage),
        ("production_write_false", test_production_write_false),
        ("P2.6.6_regression", test_p266_regression_file),
        ("P2.6.7_regression", test_p267_regression_file),
        ("P2.6.8_regression", test_p268_regression_file),
        ("P2.6.9_regression", test_p269_regression_file),
        ("P2.6.10-A_artifact_preservation", test_p2610a_artifact_preservation),
        ("production_identical_fingerprints", test_production_identical_fingerprints),
        ("firewall_and_leakage", test_firewall_and_leakage),
        ("classify_never_production_ready", test_classify_never_production_ready),
        ("missing_top_is_incomplete", test_missing_top_is_incomplete),
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
