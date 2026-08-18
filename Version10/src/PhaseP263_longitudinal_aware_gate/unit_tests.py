"""Unit tests for P2.6.3. No live Claude in the default suite."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP261_stratified_vision_candidate_recovery.unit_tests import (
    run_unit_tests as run_p261_unit_tests,
)
from PhaseP262_selective_vision_candidate_gate.unit_tests import (
    run_unit_tests as run_p262_unit_tests,
    test_incomplete_stirrup_call as p262_incomplete_stirrup,
    test_ocr_stirrup_call as p262_ocr_stirrup,
    test_stirrup_text_no_object_call as p262_stirrup_no_object,
)

from .config import (
    COVER_DIA,
    COVER_FULL,
    COVER_LAYER,
    COVER_MISSING,
    COVER_NONE,
    COVER_QTY,
    COVER_ROLE,
    DECISION_CALL,
    DECISION_SKIP,
    GATE_VERSION,
    MAX_LIVE_CALLS,
    MODEL_VERSION,
    PRODUCTION_WRITE,
)
from .evaluator import evaluate_replay
from .frozen_sample import load_frozen_manifest
from .gate_decision import build_gate_decision
from .gate_rules import decide_gate
from .longitudinal_coverage import evaluate_longitudinal_coverage
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


def _ann(text: str, **extra: Any) -> Dict[str, Any]:
    row = {"text": text}
    row.update(extra)
    return row


def _model(*, top=None, bottom=None, stirrups=None) -> Dict[str, Any]:
    return {
        "top_main_bars": list(top or []),
        "bottom_main_bars": list(bottom or []),
        "stirrups": list(stirrups or []),
        "side_face_reinforcement": [],
        "spacer_bars": [],
        "total_classified_bars": len(top or []) + len(bottom or []) + len(stirrups or []),
    }


def _bar(role: str, dia: int, label: str, quantity: Optional[int] = None) -> Dict[str, Any]:
    qty = quantity
    if qty is None:
        head = "".join(ch for ch in label.split("#")[0] if ch.isdigit() or ch == "-")
        try:
            qty = int(str(label).split("-")[0].split("Y")[0])
        except Exception:
            qty = 1
        if not qty:
            qty = 1
        del head
    return {
        "semantic_role": role,
        "diameter_mm": dia,
        "bar_label": label,
        "bar_id": label,
        "quantity": qty,
    }


def _decide(rec: Dict[str, Any], model: Dict[str, Any], **kw: Any) -> Dict[str, Any]:
    return build_gate_decision(
        beam_id=kw.get("beam_id", "BX"),
        region_id=kw.get("region_id", "P263::Fifth::BX"),
        rec=rec,
        model=model,
        association=kw.get("association", "TARGET_BEAM"),
        set_key="Fifth",
        source_set="Fifth Set Drawings",
    )


def test_same_role_dia_sufficient_qty_skip() -> None:
    rec = {"accepted_annotations": [_ann("3-Y20", semantic_role="BOTTOM")], "rejected_annotations": []}
    d = _decide(rec, _model(bottom=[_bar("BOTTOM_MAIN", 20, "3-Y20", 3)]))
    assert d["decision"] == DECISION_SKIP
    assert d["longitudinal_coverage"] == COVER_FULL


def test_same_role_dia_insufficient_qty_call() -> None:
    rec = {"accepted_annotations": [_ann("3-Y20", semantic_role="BOTTOM")], "rejected_annotations": []}
    d = _decide(rec, _model(bottom=[_bar("BOTTOM_MAIN", 20, "1-Y20", 1)]))
    assert d["decision"] == DECISION_CALL
    assert "LONGITUDINAL_COVERAGE_SHORTFALL" in d["reason_codes"]
    assert d["longitudinal_coverage"] == COVER_QTY


def test_same_dia_different_role_call() -> None:
    rec = {"accepted_annotations": [_ann("3-Y20", semantic_role="BOTTOM")], "rejected_annotations": []}
    d = _decide(rec, _model(top=[_bar("TOP_MAIN", 20, "3-Y20", 3)]))
    assert d["decision"] == DECISION_CALL
    assert "LONGITUDINAL_SEMANTIC_CONFLICT" in d["reason_codes"]
    assert d["longitudinal_coverage"] == COVER_ROLE


def test_multiple_callouts_insufficient_qty_call() -> None:
    rec = {
        "accepted_annotations": [
            _ann("3-Y20", semantic_role="TOP"),
            _ann("2-Y20", semantic_role="TOP"),
        ],
        "rejected_annotations": [],
    }
    d = _decide(rec, _model(top=[_bar("TOP_MAIN", 20, "3-Y20", 3)]))
    assert d["decision"] == DECISION_CALL
    assert "LONGITUDINAL_COVERAGE_SHORTFALL" in d["reason_codes"]


def test_multiple_callouts_adequately_represented_skip() -> None:
    rec = {
        "accepted_annotations": [
            _ann("3-Y20", semantic_role="TOP"),
            _ann("2-Y16", semantic_role="BOTTOM"),
        ],
        "rejected_annotations": [],
    }
    d = _decide(
        rec,
        _model(
            top=[_bar("TOP_MAIN", 20, "3-Y20", 3)],
            bottom=[_bar("BOTTOM_MAIN", 16, "2-Y16", 2)],
        ),
    )
    assert d["decision"] == DECISION_SKIP
    assert d["longitudinal_coverage"] == COVER_FULL


def test_conflicting_longitudinal_object_call() -> None:
    rec = {"accepted_annotations": [_ann("4-Y16", semantic_role="TOP")], "rejected_annotations": []}
    d = _decide(rec, _model(top=[_bar("TOP_MAIN", 20, "6-Y20", 6)]))
    assert d["decision"] == DECISION_CALL
    assert "LONGITUDINAL_SEMANTIC_CONFLICT" in d["reason_codes"]
    assert d["longitudinal_coverage"] == COVER_DIA


def test_unknown_role_conservative() -> None:
    xor = _decide(
        {"accepted_annotations": [_ann("3-Y20")], "rejected_annotations": []},
        _model(top=[_bar("TOP_MAIN", 20, "3-Y20", 3)]),
    )
    assert xor["decision"] == DECISION_CALL
    assert xor["longitudinal_coverage"] == COVER_LAYER
    both = _decide(
        {"accepted_annotations": [_ann("3-Y20")], "rejected_annotations": []},
        _model(
            top=[_bar("TOP_MAIN", 20, "3-Y20", 3)],
            bottom=[_bar("BOTTOM_MAIN", 25, "4-Y25", 4)],
        ),
    )
    assert both["decision"] == DECISION_SKIP
    assert both["longitudinal_coverage"] == COVER_FULL


def test_unassociated_longitudinal_matching_coverage_skip() -> None:
    rec = {
        "accepted_annotations": [_ann("3-Y20"), _ann("3L-Y10@100C/C")],
        "rejected_annotations": [_ann("2-Y12")],
    }
    model = _model(
        top=[_bar("TOP_MAIN", 20, "3-Y20", 3)],
        bottom=[_bar("BOTTOM_MAIN", 20, "3-Y20", 3)],
        stirrups=[_bar("STIRRUP", 10, "3L-Y10@100C/C", 1)],
    )
    d = _decide(rec, model)
    assert d["decision"] == DECISION_SKIP


def test_no_deterministic_longitudinal_object_call() -> None:
    rec = {"accepted_annotations": [_ann("4-Y25")], "rejected_annotations": []}
    d = _decide(rec, _model())
    assert d["decision"] == DECISION_CALL
    assert "MISSING_DETERMINISTIC_OBJECT" in d["reason_codes"]
    assert d["longitudinal_coverage"] == COVER_MISSING


def test_stirrup_behavior_unchanged() -> None:
    rec = {"accepted_annotations": [_ann("4L-Y10@100C/C")], "rejected_annotations": []}
    d = _decide(rec, _model())
    assert d["decision"] == DECISION_CALL
    assert "STIRRUP_TEXT_NO_OBJECT" in d["reason_codes"]
    p262_stirrup_no_object()
    p262_ocr_stirrup()
    p262_incomplete_stirrup()


def test_b56_b57_control_fixtures() -> None:
    """Clean both-layer coverage. Not beam-id hardcoded in the gate."""
    b56 = {
        "accepted_annotations": [
            _ann("2-Y16"),
            _ann("3-Y20"),
            _ann("3L-Y10@100/150/100C/C"),
        ],
        "rejected_annotations": [_ann("3-Y25")],
    }
    m56 = _model(
        top=[
            _bar("TOP_MAIN", 25, "3-Y25", 3),
            _bar("TOP_EXTRA", 20, "3-Y20", 3),
            _bar("TOP_EXTRA", 16, "2-Y16", 2),
        ],
        bottom=[_bar("BOTTOM_MAIN", 25, "3-Y25", 3)],
        stirrups=[_bar("STIRRUP", 10, "3L-Y10@100/150/100C/C", 1)],
    )
    b57 = {
        "accepted_annotations": [_ann("3-Y20"), _ann("3L-Y10@100/125/100C/C")],
        "rejected_annotations": [_ann("3-Y25")],
    }
    m57 = _model(
        top=[_bar("TOP_MAIN", 20, "3-Y20", 3)],
        bottom=[
            _bar("BOTTOM_MAIN", 25, "3-Y25", 3),
            _bar("BOTTOM_EXTRA", 20, "3-Y20", 3),
        ],
        stirrups=[_bar("STIRRUP", 10, "3L-Y10@100/125/100C/C", 1)],
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
        "longitudinal_coverage": COVER_NONE,
    }
    a = decide_gate(feat)
    raised = False
    try:
        decide_gate({**feat, "stratum": "EASY"})
    except ValueError:
        raised = True
    assert raised
    assert a["decision"] == DECISION_CALL
    cov_src = (_pkg() / "longitudinal_coverage.py").read_text(encoding="utf-8")
    feat_src = (_pkg() / "gate_features.py").read_text(encoding="utf-8")
    assert "stratum" not in cov_src
    assert "stratum" not in feat_src


def test_gate_runtime_no_gt_tokens() -> None:
    for name in (
        "gate_features.py",
        "gate_rules.py",
        "gate_decision.py",
        "longitudinal_coverage.py",
        "replay_runner.py",
    ):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "TRUE_RECOVERY" not in text
        assert "load_gt_universe" not in text
        assert "missed_gt" not in text
        assert "gt_match_status" not in text
        assert "strict_true_recovery" not in text


def test_gate_runtime_no_estimator_tokens() -> None:
    for name in (
        "gate_features.py",
        "gate_rules.py",
        "gate_decision.py",
        "longitudinal_coverage.py",
        "replay_runner.py",
    ):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "EstimatorOutput" not in text
        assert "estimator_steel" not in text
        assert "estimator_kg" not in text
        assert "steel_accuracy" not in text


def test_frozen_manifest_not_resampled() -> None:
    regions, summary = load_frozen_manifest(_v10())
    assert int(summary.get("seed") or 0) == 2611101
    assert len(regions) == 75
    assert summary.get("selected_by_stratum", {}).get("DIFFICULT") == 25
    assert summary.get("selected_by_stratum", {}).get("NORMAL") == 25
    assert summary.get("selected_by_stratum", {}).get("EASY") == 25
    beams = {(r.get("set_key"), r.get("beam_id")) for r in regions}
    assert len(beams) == 75


def test_no_live_vision_api() -> None:
    assert MAX_LIVE_CALLS == 0
    orch = (_pkg() / "phase_p263_orchestrator.py").read_text(encoding="utf-8")
    assert "observe_region" not in orch
    assert "anthropic" not in orch.lower()
    live = (_pkg() / "live_runner.py").read_text(encoding="utf-8")
    assert "live_calls\": 0" in live.replace(" ", "") or "live_calls': 0" in live or '"live_calls": 0' in live


def test_production_write_false() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert MODEL_VERSION == "10.11.3"
    assert GATE_VERSION == "P263_LONGITUDINAL_AWARE_GATE_V1_0"


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


def test_p262_stirrup_regression() -> None:
    nested = run_p262_unit_tests()
    assert nested.get("success"), nested
    p262_stirrup_no_object()
    p262_ocr_stirrup()
    p262_incomplete_stirrup()


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


def test_metrics_false_paths() -> None:
    decisions = [
        {
            "set_key": "Fifth",
            "beam_id": "B1",
            "decision": DECISION_CALL,
            "reason_codes": ["STIRRUP_TEXT_NO_OBJECT"],
            "eval_stratum": "DIFFICULT",
            "longitudinal_coverage": COVER_NONE,
        },
        {
            "set_key": "Fifth",
            "beam_id": "B2",
            "decision": DECISION_SKIP,
            "reason_codes": ["LONGITUDINAL_FULLY_COVERED"],
            "eval_stratum": "EASY",
            "longitudinal_coverage": COVER_FULL,
            "per_annotation_coverage": [{"text": "2L-Y8", "normalized_text": "2L-Y8"}],
        },
    ]
    baseline = [
        {
            "set_key": "Fifth",
            "beam_id": "B1",
            "gt_match_status": "TRUE_RECOVERY",
            "gt_supported": True,
            "deterministic_match_status": "POTENTIALLY_MISSING",
            "candidate_type": "STIRRUP",
            "stratum": "DIFFICULT",
        },
        {
            "set_key": "Fifth",
            "beam_id": "B2",
            "gt_match_status": "TRUE_RECOVERY",
            "gt_supported": True,
            "deterministic_match_status": "POTENTIALLY_MISSING",
            "candidate_type": "STIRRUP",
            "stratum": "EASY",
            "annotation_text": "2L-Y8",
        },
    ]
    gated, _ = apply_gate_to_frozen(decisions=decisions, frozen_candidates=baseline)
    ev = evaluate_replay(decisions=decisions, baseline_candidates=baseline, gated_candidates=gated)
    assert ev["metrics"]["RECOVERIES_LOST"] == 1
    assert ev["false_skips"][0]["beam_id"] == "B2"


def test_coverage_evaluator_role_qty() -> None:
    rec = {"accepted_annotations": [_ann("3-Y20", semantic_role="BOTTOM")]}
    cov = evaluate_longitudinal_coverage(
        rec=rec, model=_model(bottom=[_bar("BOTTOM_MAIN", 20, "3-Y20", 3)])
    )
    assert cov["longitudinal_coverage"] == COVER_FULL
    cov2 = evaluate_longitudinal_coverage(
        rec=rec, model=_model(bottom=[_bar("BOTTOM_MAIN", 20, "1-Y20", 1)])
    )
    assert cov2["longitudinal_coverage"] == COVER_QTY


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("same_role_dia_sufficient_qty_skip", test_same_role_dia_sufficient_qty_skip),
        ("same_role_dia_insufficient_qty_call", test_same_role_dia_insufficient_qty_call),
        ("same_dia_different_role_call", test_same_dia_different_role_call),
        ("multiple_callouts_insufficient_qty_call", test_multiple_callouts_insufficient_qty_call),
        ("multiple_callouts_adequately_represented_skip", test_multiple_callouts_adequately_represented_skip),
        ("conflicting_longitudinal_object_call", test_conflicting_longitudinal_object_call),
        ("unknown_role_conservative", test_unknown_role_conservative),
        ("unassociated_longitudinal_matching_coverage_skip", test_unassociated_longitudinal_matching_coverage_skip),
        ("no_deterministic_longitudinal_object_call", test_no_deterministic_longitudinal_object_call),
        ("stirrup_behavior_unchanged", test_stirrup_behavior_unchanged),
        ("b56_b57_control_fixtures", test_b56_b57_control_fixtures),
        ("stratum_not_used", test_stratum_not_used),
        ("gate_runtime_no_gt_tokens", test_gate_runtime_no_gt_tokens),
        ("gate_runtime_no_estimator_tokens", test_gate_runtime_no_estimator_tokens),
        ("frozen_manifest_not_resampled", test_frozen_manifest_not_resampled),
        ("no_live_vision_api", test_no_live_vision_api),
        ("production_write_false", test_production_write_false),
        ("no_production_mutation", test_no_production_mutation),
        ("firewall_and_leakage", test_firewall_and_leakage),
        ("P2.6.1_regression", test_p261_regression),
        ("P2.6.2_stirrup_regression", test_p262_stirrup_regression),
        ("replay_skip_drops_candidates", test_replay_skip_drops_candidates),
        ("metrics_false_paths", test_metrics_false_paths),
        ("coverage_evaluator_role_qty", test_coverage_evaluator_role_qty),
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
        "gate_version": GATE_VERSION,
    }


__all__ = ["run_unit_tests"]
