"""Unit tests for P2.6.10-A. No live Claude. Does not change P2.6.6–P2.6.9 routing."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .config import GATE_VERSION, MODEL_VERSION, PRODUCTION_ACTION, PRODUCTION_WRITE, SHADOW_ONLY
from .evaluator import classify_final_decision, classify_phase_status, classify_reusability
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    prior_phase_unit_ok,
    runtime_leakage_scan,
)
from .region_builder import _tighten_detail_y
from .title_localizer import parse_beam_title


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def test_parse_beam_title() -> None:
    rec = parse_beam_title("%%UB55(300X1100)")
    assert rec is not None
    assert rec["beam_id"] == "B55"
    assert rec["width_mm"] == 300.0
    assert rec["depth_mm"] == 1100.0
    assert parse_beam_title("random note") is None


def test_detail_y_split_excludes_other_elevation_row() -> None:
    mark = {"x": 0.0, "y": 0.0, "depth_mm": 1000.0, "beam_id": "BX"}
    extent = (-2000.0, -4000.0, 2000.0, 4000.0)
    titles = [
        {"beam_id": "BX", "x": 0.0, "y": 0.0},
        {"beam_id": "BY", "x": 100.0, "y": -3200.0},
    ]
    out = _tighten_detail_y(extent, mark, titles, "BX")
    assert out[1] > extent[1]
    assert out[1] > -2000.0
    assert out[3] <= extent[3]
    # A title above must not cut through the kept beam body.
    titles_above = [
        {"beam_id": "BX", "x": 0.0, "y": 0.0},
        {"beam_id": "BZ", "x": 100.0, "y": 2500.0},
    ]
    out2 = _tighten_detail_y(extent, mark, titles_above, "BX")
    assert out2[3] >= 2000.0


def test_localization_modules_independent_of_association() -> None:
    forbidden = (
        "annotations_by_beam",
        "PhaseP266_",
        "PhaseP267_",
        "PhaseP268_",
        "PhaseP269_",
        "associate_annotations",
        "reinforcement_annotations.json",
    )
    for name in ("title_localizer.py", "region_builder.py", "cropper.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        for tok in forbidden:
            assert tok not in text, f"{name} contains {tok}"


def test_no_beam_id_hardcoding_in_runtime() -> None:
    for name in ("title_localizer.py", "region_builder.py", "cropper.py", "quality.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        for token in ("B128", "B141", "B55", "B66", "B161", "B65"):
            assert token not in text, f"{name} contains {token}"


def test_no_gt_usage() -> None:
    for name in ("title_localizer.py", "region_builder.py", "cropper.py", "dataset.py", "evaluator.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "TRUE_RECOVERY" not in text
        assert "load_gt_universe" not in text
        assert "EstimatorOutput" not in text


def test_production_write_false() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert MODEL_VERSION == "10.11.10"
    assert GATE_VERSION == "P2610A_BEAM_REGION_CROP_AUDIT_V1_0"
    assert SHADOW_ONLY is True
    assert PRODUCTION_ACTION == "NO_CHANGE"


def test_p266_regression_file() -> None:
    info = prior_phase_unit_ok(_v10(), "PhaseP266_semantic_longitudinal_resolver", 36)
    assert info.get("ok") is True


def test_p267_regression_file() -> None:
    info = prior_phase_unit_ok(_v10(), "PhaseP267_live_semantic_arbitration", 31)
    assert info.get("ok") is True


def test_p268_regression_file() -> None:
    info = prior_phase_unit_ok(_v10(), "PhaseP268_evidence_conflict_arbitration", 27)
    assert info.get("ok") is True


def test_p269_regression_file() -> None:
    info = prior_phase_unit_ok(_v10(), "PhaseP269_reinforcement_group_interpretation", 20)
    assert info.get("ok") is True


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
    recs = [
        {
            "crops": {
                "detail": {"quality": {"beam_geometry_included": True, "vision_readiness": "READY"}},
                "context": {"quality": {}},
            },
            "mark": {"x": 1, "y": 1},
            "annotation_association_dependency": False,
        }
    ] * 6
    b55 = {"Vision_readiness": "READY"}
    reuse = classify_reusability(recs)
    decision = classify_final_decision(
        reusability=reuse,
        records=recs,
        b55=b55,
        tests_ok=True,
        fingerprints_ok=True,
    )
    assert "PRODUCTION_READY" not in decision
    status = classify_phase_status(
        tests_ok=True,
        fingerprints_ok=True,
        six_beams=True,
        crops_complete=True,
        reusability=reuse,
        final_decision=decision,
    )
    assert status in ("PASS", "PARTIAL", "FAILED")


def test_renderer_is_m1_region_renderer() -> None:
    text = (_pkg() / "cropper.py").read_text(encoding="utf-8")
    assert "render_dxf_region_to_png" in text
    assert "PhaseM.1_engineering_vision_dataset" in text


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("parse_beam_title", test_parse_beam_title),
        ("detail_y_split_excludes_other_elevation_row", test_detail_y_split_excludes_other_elevation_row),
        ("localization_modules_independent_of_association", test_localization_modules_independent_of_association),
        ("no_beam_id_hardcoding_in_runtime", test_no_beam_id_hardcoding_in_runtime),
        ("no_gt_usage", test_no_gt_usage),
        ("production_write_false", test_production_write_false),
        ("P2.6.6_regression", test_p266_regression_file),
        ("P2.6.7_regression", test_p267_regression_file),
        ("P2.6.8_regression", test_p268_regression_file),
        ("P2.6.9_regression", test_p269_regression_file),
        ("production_identical_fingerprints", test_production_identical_fingerprints),
        ("firewall_and_leakage", test_firewall_and_leakage),
        ("classify_never_production_ready", test_classify_never_production_ready),
        ("renderer_is_m1_region_renderer", test_renderer_is_m1_region_renderer),
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
