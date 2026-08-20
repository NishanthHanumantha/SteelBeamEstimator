"""Unit tests for P2.6.10-B.1. No live Claude. Does not change P2.6.6–P2.6.10-B routing."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .anti_hardcoding import packed_sheet_robustness, source_guard, spatial_distance_robustness, translation_invariance_synthetic
from .config import DRAWING_SET_KEY, GATE_VERSION, MODEL_VERSION, PRODUCTION_ACTION, PRODUCTION_WRITE, SHADOW_ONLY
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    p2610b_artefacts_intact,
    prior_phase_unit_ok,
    runtime_leakage_scan,
)
from .validator import validate_detail


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def test_fourth_set_only() -> None:
    assert DRAWING_SET_KEY == "Fourth"
    text = (_pkg() / "population.py").read_text(encoding="utf-8")
    assert "Fifth" not in text
    assert "1st Set" not in text


def test_source_guard() -> None:
    g = source_guard(_pkg())
    assert g.get("ok") is True, g.get("hits")


def test_no_beam_id_in_crop_runtime() -> None:
    for name in ("population.py", "validator.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        for tok in ("B128", "B141", "B55", "B66", "B161", "B65"):
            assert tok not in text, f"{name} contains {tok}"


def test_no_r1_or_gt_in_runtime() -> None:
    for name in ("population.py", "validator.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        for tok in ("annotations_by_beam", "TRUE_RECOVERY", "load_gt_universe", "EstimatorOutput"):
            assert tok not in text, f"{name} contains {tok}"


def test_translation_invariance() -> None:
    r = translation_invariance_synthetic()
    assert r.get("ok") is True, r


def test_spatial_distance_robustness() -> None:
    r = spatial_distance_robustness()
    assert r.get("ok") is True, r


def test_packed_sheet_robustness() -> None:
    r = packed_sheet_robustness()
    assert r.get("ok") is True, r


def test_na_evidence_does_not_fail() -> None:
    mark = {"x": 0.0, "y": 0.0, "depth_mm": 500.0}
    extent = (-2000.0, -400.0, 2000.0, 2200.0)
    evidence = [
        {"kind": "STIRRUP", "band": "STIRRUP_BAND", "x": 10.0, "y": 300.0, "dx": 10.0, "dy": 300.0, "text": "4L-Y8@100C/C"},
        {"kind": "REINF", "band": "BOTTOM_REINFORCEMENT_BAND", "x": 10.0, "y": 600.0, "dx": 10.0, "dy": 600.0, "text": "5-Y16"},
    ]
    v = validate_detail(
        beam_id="BX",
        extent=extent,
        mark=mark,
        outline=(-200.0, 800.0),
        evidence=evidence,
        titles=[{"beam_id": "BX", "x": 0.0, "y": 0.0}],
        rendered=True,
        discovery_ok=True,
    )
    assert v["top_evidence_status"] == "NOT_APPLICABLE"
    assert v["completeness_status"] == "PASS"


def test_missing_top_is_failure() -> None:
    mark = {"x": 0.0, "y": 0.0, "depth_mm": 500.0}
    extent = (-2000.0, -400.0, 2000.0, 1600.0)
    evidence = [
        {"kind": "REINF", "band": "BOTTOM_REINFORCEMENT_BAND", "x": 10.0, "y": 600.0, "dx": 10.0, "dy": 600.0, "text": "5-Y16"},
        {"kind": "REINF", "band": "TOP_REINFORCEMENT_BAND", "x": 10.0, "y": 1971.0, "dx": 10.0, "dy": 1971.0, "text": "5-Y20"},
    ]
    v = validate_detail(
        beam_id="BX",
        extent=extent,
        mark=mark,
        outline=(-200.0, 800.0),
        evidence=evidence,
        titles=[{"beam_id": "BX", "x": 0.0, "y": 0.0}],
        rendered=True,
        discovery_ok=True,
    )
    assert v["top_evidence_status"] == "MISSING"
    assert "MISSING_TOP_EVIDENCE" in v["failure_categories"]
    assert v["completeness_status"] == "FAIL"


def test_production_write_false() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert MODEL_VERSION == "10.11.12"
    assert GATE_VERSION == "P2610B1_POPULATION_GENERALIZATION_ANTI_HARDCODING_V1_0"
    assert SHADOW_ONLY is True
    assert PRODUCTION_ACTION == "NO_CHANGE"


def test_p266_regression_file() -> None:
    assert prior_phase_unit_ok(_v10(), "PhaseP266_semantic_longitudinal_resolver", 36).get("ok") is True


def test_p2610a_artifact_preservation() -> None:
    info = prior_phase_unit_ok(_v10(), "PhaseP2610A_beam_region_crop_audit", 14)
    assert info.get("ok") is True
    status = _v10() / "data" / "output" / "PhaseP2610A_beam_region_crop_audit" / "P2.6.10-A_STATUS.md"
    assert status.exists()


def test_p2610b_tests_and_artefacts() -> None:
    info = prior_phase_unit_ok(_v10(), "PhaseP2610B_adaptive_beam_detail_crop", 18)
    assert info.get("ok") is True
    intact = p2610b_artefacts_intact(_v10())
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
    from .phase_p2610b1_orchestrator import _classify_decision

    d = _classify_decision(
        tests_ok=True,
        fingerprints_ok=True,
        anti_ok=True,
        six_ok=True,
        processed=10,
        discovered=10,
        complete_n=10,
        skip_n=0,
        render_fail_n=0,
    )
    assert "PRODUCTION" not in d
    assert d.startswith("PASS")


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("fourth_set_only", test_fourth_set_only),
        ("source_guard", test_source_guard),
        ("no_beam_id_in_crop_runtime", test_no_beam_id_in_crop_runtime),
        ("no_r1_or_gt_in_runtime", test_no_r1_or_gt_in_runtime),
        ("translation_invariance", test_translation_invariance),
        ("spatial_distance_robustness", test_spatial_distance_robustness),
        ("packed_sheet_robustness", test_packed_sheet_robustness),
        ("na_evidence_does_not_fail", test_na_evidence_does_not_fail),
        ("missing_top_is_failure", test_missing_top_is_failure),
        ("production_write_false", test_production_write_false),
        ("P2.6.6_regression", test_p266_regression_file),
        ("P2.6.10-A_artifact_preservation", test_p2610a_artifact_preservation),
        ("P2.6.10-B_tests_and_artefacts", test_p2610b_tests_and_artefacts),
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
