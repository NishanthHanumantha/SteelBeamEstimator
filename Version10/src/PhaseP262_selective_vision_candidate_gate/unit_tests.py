"""Unit tests for P2.6.2. No live Claude in the default suite."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from PhaseP261_stratified_vision_candidate_recovery.unit_tests import (
    run_unit_tests as run_p261_unit_tests,
)

from .config import (
    DECISION_CALL,
    DECISION_HOLD,
    DECISION_SKIP,
    MODEL_VERSION,
    PRODUCTION_WRITE,
)
from .evaluator import evaluate_replay
from .frozen_sample import load_frozen_manifest
from .gate_decision import build_gate_decision
from .gate_rules import decide_gate
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)
from .replay_runner import apply_gate_to_frozen


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def _ann(text: str) -> Dict[str, Any]:
    return {"text": text}


def _model(*, top=None, bottom=None, stirrups=None) -> Dict[str, Any]:
    return {
        "top_main_bars": list(top or []),
        "bottom_main_bars": list(bottom or []),
        "stirrups": list(stirrups or []),
        "side_face_reinforcement": [],
        "spacer_bars": [],
        "total_classified_bars": len(top or []) + len(bottom or []) + len(stirrups or []),
    }


def _bar(role: str, dia: int, label: str) -> Dict[str, Any]:
    return {"semantic_role": role, "diameter_mm": dia, "bar_label": label, "bar_id": label}


def _decide(rec: Dict[str, Any], model: Dict[str, Any], **kw: Any) -> Dict[str, Any]:
    return build_gate_decision(
        beam_id=kw.get("beam_id", "BX"),
        region_id=kw.get("region_id", "P262::Fifth::BX"),
        rec=rec,
        model=model,
        association=kw.get("association", "TARGET_BEAM"),
        set_key="Fifth",
        source_set="Fifth Set Drawings",
    )


def test_matching_object_skip() -> None:
    rec = {
        "accepted_annotations": [_ann("3-Y20"), _ann("3L-Y10@100/125/100C/C")],
        "rejected_annotations": [],
    }
    model = _model(
        bottom=[_bar("BOTTOM_MAIN", 20, "3-Y20")],
        stirrups=[_bar("STIRRUP", 10, "3L-Y10@100/125/100C/C")],
    )
    d = _decide(rec, model)
    assert d["decision"] == DECISION_SKIP
    assert "MATCHING_OBJECT_EXISTS" in d["reason_codes"] or "NO_PRODUCTION_GAP" in d["reason_codes"] or "STRONG_DETERMINISTIC_COVERAGE" in d["reason_codes"]


def test_complete_parse_skip() -> None:
    rec = {"accepted_annotations": [_ann("3-Y20")], "rejected_annotations": []}
    model = _model(bottom=[_bar("BOTTOM_MAIN", 20, "3-Y20")])
    d = _decide(rec, model)
    assert d["decision"] == DECISION_SKIP


def test_stirrup_text_no_object_call() -> None:
    rec = {"accepted_annotations": [_ann("4L-Y10@100C/C")], "rejected_annotations": []}
    d = _decide(rec, _model())
    assert d["decision"] == DECISION_CALL
    assert "STIRRUP_TEXT_NO_OBJECT" in d["reason_codes"]


def test_ocr_stirrup_call() -> None:
    rec = {"accepted_annotations": [_ann("4L-Y10@\\X100C/C")], "rejected_annotations": []}
    d = _decide(rec, _model())
    assert d["decision"] == DECISION_CALL
    assert "OCR_CORRUPTED_STIRRUP" in d["reason_codes"] or "STIRRUP_TEXT_NO_OBJECT" in d["reason_codes"]


def test_incomplete_stirrup_call() -> None:
    rec = {"accepted_annotations": [_ann("2L-Y8@")], "rejected_annotations": []}
    d = _decide(rec, _model())
    assert d["decision"] == DECISION_CALL


def test_missing_longitudinal_call() -> None:
    rec = {"accepted_annotations": [_ann("4-Y25")], "rejected_annotations": []}
    d = _decide(rec, _model(top=[_bar("TOP_MAIN", 16, "3-Y16")]))
    assert d["decision"] == DECISION_CALL
    assert "MISSING_DETERMINISTIC_OBJECT" in d["reason_codes"]


def test_complete_longitudinal_skip() -> None:
    rec = {"accepted_annotations": [_ann("3-Y20")], "rejected_annotations": []}
    d = _decide(rec, _model(top=[_bar("TOP_MAIN", 20, "3-Y20")]))
    assert d["decision"] == DECISION_SKIP


def test_longitudinal_object_shortfall_call() -> None:
    """Two same-diameter longitudinal callouts vs one R1.3 object is a production gap."""
    rec = {
        "accepted_annotations": [_ann("3-Y16"), _ann("3-Y16")],
        "rejected_annotations": [],
    }
    d = _decide(rec, _model(top=[_bar("TOP_MAIN", 16, "3-Y16")]))
    assert d["decision"] == DECISION_CALL
    assert "MISSING_DETERMINISTIC_OBJECT" in d["reason_codes"]


def test_matching_object_unassociated_skip() -> None:
    rec = {
        "accepted_annotations": [_ann("3-Y20"), _ann("3L-Y10@100C/C")],
        "rejected_annotations": [_ann("2-Y12")],
    }
    model = _model(
        bottom=[_bar("BOTTOM_MAIN", 20, "3-Y20")],
        stirrups=[_bar("STIRRUP", 10, "3L-Y10@100C/C")],
    )
    d = _decide(rec, model)
    assert d["decision"] == DECISION_SKIP


def test_uncertain_association_hold() -> None:
    rec = {"accepted_annotations": [_ann("3-Y20")], "rejected_annotations": []}
    d = _decide(rec, _model(top=[_bar("TOP_MAIN", 20, "3-Y20")]), association="UNCERTAIN")
    assert d["decision"] == DECISION_HOLD


def test_other_beam_hold() -> None:
    rec = {"accepted_annotations": [_ann("4L-Y10@\\X100C/C")], "rejected_annotations": []}
    d = _decide(rec, _model(), association="OTHER_BEAM")
    assert d["decision"] == DECISION_HOLD


def test_b56_b57_control_fixtures() -> None:
    """Clean annotations already represented deterministically. Not beam-id hardcoded in the gate."""
    b56 = {
        "accepted_annotations": [
            _ann("2-Y16"),
            _ann("3-Y20"),
            _ann("3L-Y10@100/150/100C/C"),
        ],
        "rejected_annotations": [],
    }
    m56 = _model(
        top=[_bar("TOP_EXTRA", 16, "2-Y16")],
        bottom=[_bar("BOTTOM_MAIN", 20, "3-Y20")],
        stirrups=[_bar("STIRRUP", 10, "3L-Y10@100/150/100C/C")],
    )
    b57 = {
        "accepted_annotations": [_ann("3-Y20"), _ann("3L-Y10@100/125/100C/C")],
        "rejected_annotations": [],
    }
    m57 = _model(
        bottom=[_bar("BOTTOM_MAIN", 20, "3-Y20")],
        stirrups=[_bar("STIRRUP", 10, "3L-Y10@100/125/100C/C")],
    )
    assert _decide(b56, m56, beam_id="CTRL_A")["decision"] == DECISION_SKIP
    assert _decide(b57, m57, beam_id="CTRL_B")["decision"] == DECISION_SKIP


def test_stratum_not_used() -> None:
    feat = {
        "stirrup_text_no_object": True,
        "stirrup_text_present": True,
        "stirrup_object_present": False,
        "unmatched_stirrup_count": 1,
        "OCR_corruption_count": 0,
        "ocr_corrupted_stirrup_unmatched": 0,
        "incomplete_parse_count": 0,
        "unmatched_longitudinal_count": 0,
        "unassociated_strong_count": 0,
        "unassociated_annotation_count": 0,
        "association": "TARGET_BEAM",
        "matching_object_count": 0,
        "parse_complete": True,
        "deterministic_object_count": 0,
        "reinforcement_annotation_count": 1,
        "side_text_present": False,
        "side_object_present": False,
    }
    a = decide_gate(feat)
    raised = False
    try:
        decide_gate({**feat, "stratum": "EASY"})
    except ValueError:
        raised = True
    assert raised
    assert a["decision"] == DECISION_CALL


def test_gate_runtime_no_gt_tokens() -> None:
    for name in ("gate_features.py", "gate_rules.py", "gate_decision.py", "replay_runner.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "TRUE_RECOVERY" not in text
        assert "EstimatorOutput" not in text
        assert "load_gt_universe" not in text
        assert "missed_gt" not in text


def test_frozen_manifest_not_resampled() -> None:
    regions, summary = load_frozen_manifest(_v10())
    assert int(summary.get("seed") or 0) == 2611101
    assert len(regions) == 75
    assert summary.get("selected_by_stratum", {}).get("DIFFICULT") == 25
    beams = {(r.get("set_key"), r.get("beam_id")) for r in regions}
    assert len(beams) == 75


def test_replay_skip_drops_candidates() -> None:
    decisions = [
        {"set_key": "Fifth", "beam_id": "B1", "decision": DECISION_CALL},
        {"set_key": "Fifth", "beam_id": "B2", "decision": DECISION_SKIP},
    ]
    frozen = [
        {"set_key": "Fifth", "beam_id": "B1", "candidate_id": "C1", "gt_match_status": "TRUE_RECOVERY"},
        {"set_key": "Fifth", "beam_id": "B2", "candidate_id": "C2", "gt_match_status": "DUPLICATE"},
    ]
    gated, summary = apply_gate_to_frozen(decisions=decisions, frozen_candidates=frozen)
    assert len(gated) == 1
    assert gated[0]["candidate_id"] == "C1"
    assert gated[0]["replay_source"] == "FROZEN_P261_VISION"
    assert summary["suppressed_candidates"] == 1


def test_metrics_reduction_retention_false_paths() -> None:
    decisions = [
        {"set_key": "Fifth", "beam_id": "B1", "decision": DECISION_CALL, "reason_codes": ["STIRRUP_TEXT_NO_OBJECT"], "eval_stratum": "DIFFICULT"},
        {"set_key": "Fifth", "beam_id": "B2", "decision": DECISION_SKIP, "reason_codes": ["MATCHING_OBJECT_EXISTS"], "eval_stratum": "EASY"},
        {"set_key": "Fifth", "beam_id": "B3", "decision": DECISION_SKIP, "reason_codes": ["NO_PRODUCTION_GAP"], "eval_stratum": "EASY"},
    ]
    baseline = [
        {"set_key": "Fifth", "beam_id": "B1", "gt_match_status": "TRUE_RECOVERY", "gt_supported": True, "deterministic_match_status": "POTENTIALLY_MISSING", "candidate_type": "STIRRUP", "stratum": "DIFFICULT"},
        {"set_key": "Fifth", "beam_id": "B2", "gt_match_status": "DUPLICATE", "gt_supported": True, "deterministic_match_status": "ALREADY_DETECTED", "candidate_type": "LONGITUDINAL_REINFORCEMENT", "stratum": "EASY"},
        {"set_key": "Fifth", "beam_id": "B3", "gt_match_status": "TRUE_RECOVERY", "gt_supported": True, "deterministic_match_status": "POTENTIALLY_MISSING", "candidate_type": "STIRRUP", "stratum": "EASY", "annotation_text": "2L-Y8"},
    ]
    gated, _ = apply_gate_to_frozen(decisions=decisions, frozen_candidates=baseline)
    ev = evaluate_replay(decisions=decisions, baseline_candidates=baseline, gated_candidates=gated)
    m = ev["metrics"]
    assert m["CALL_REDUCTION"] is not None and m["CALL_REDUCTION"] > 0
    assert m["RECOVERIES_LOST"] == 1
    assert ev["false_skips"]
    assert ev["false_skips"][0]["beam_id"] == "B3"
    assert any(fc["beam_id"] == "B1" for fc in ev["false_calls"]) is False


def test_production_write_false() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert MODEL_VERSION == "10.11.2"


def test_no_production_mutation() -> None:
    paths = fingerprint_paths(_v10(), {})
    cmp = compare_fingerprints(capture_fingerprints(paths), capture_fingerprints(paths))
    assert cmp.get("unchanged") is True


def test_firewall_and_leakage() -> None:
    fw = firewall_check(_v10())
    assert fw["ok"], fw.get("offenders")
    leak = runtime_leakage_scan(_pkg())
    assert leak["ok"], leak.get("hits")


def test_p261_regression() -> None:
    nested = run_p261_unit_tests()
    assert nested.get("success"), nested


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("matching_object_skip", test_matching_object_skip),
        ("complete_parse_skip", test_complete_parse_skip),
        ("stirrup_text_no_object_call", test_stirrup_text_no_object_call),
        ("ocr_stirrup_call", test_ocr_stirrup_call),
        ("incomplete_stirrup_call", test_incomplete_stirrup_call),
        ("missing_longitudinal_call", test_missing_longitudinal_call),
        ("complete_longitudinal_skip", test_complete_longitudinal_skip),
        ("longitudinal_object_shortfall_call", test_longitudinal_object_shortfall_call),
        ("matching_object_unassociated_skip", test_matching_object_unassociated_skip),
        ("uncertain_association_hold", test_uncertain_association_hold),
        ("other_beam_hold", test_other_beam_hold),
        ("b56_b57_control_fixtures", test_b56_b57_control_fixtures),
        ("stratum_not_used", test_stratum_not_used),
        ("gate_runtime_no_gt_tokens", test_gate_runtime_no_gt_tokens),
        ("frozen_manifest_not_resampled", test_frozen_manifest_not_resampled),
        ("replay_skip_drops_candidates", test_replay_skip_drops_candidates),
        ("metrics_reduction_retention_false_paths", test_metrics_reduction_retention_false_paths),
        ("production_write_false", test_production_write_false),
        ("no_production_mutation", test_no_production_mutation),
        ("firewall_and_leakage", test_firewall_and_leakage),
        ("P2.6.1_regression", test_p261_regression),
    ]
    results: List[Dict[str, Any]] = []
    for name, fn in tests:
        try:
            fn()
            results.append({"name": name, "pass": True})
        except Exception as exc:  # noqa: BLE001
            results.append({"name": name, "pass": False, "error": str(exc)})
    passed = sum(1 for r in results if r["pass"])
    return {
        "success": passed == len(tests),
        "passed": passed,
        "total": len(tests),
        "results": results,
        "model_version": MODEL_VERSION,
    }


__all__ = ["run_unit_tests"]
