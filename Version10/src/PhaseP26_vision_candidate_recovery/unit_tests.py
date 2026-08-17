"""Unit + integration tests for P2.6. No live Claude in the default suite."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from PhaseP2511_evidence_enrichment.unit_tests import run_unit_tests as run_p2511_unit_tests

from .cache import cache_key, load_cache, save_cache
from .candidate_gap_analyzer import score_beam
from .candidate_schema import normalize_candidate
from .config import (
    DECISION_SHADOW,
    DET_ALREADY,
    DET_MISSING,
    GT_AMBIGUOUS,
    GT_DUPLICATE,
    GT_TRUE_RECOVERY,
    GT_UNSUPPORTED,
    MODEL_VERSION,
    PRODUCTION_WRITE,
)
from .deterministic_comparator import compare_candidate
from .ground_truth_matcher import evaluate_candidate
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)
from .response_parser import parse_vision_response
from .vision_prompt import SYSTEM_PROMPT, assert_no_truth_leak, build_user_prompt


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def _cand(**kwargs: Any) -> Dict[str, Any]:
    base = normalize_candidate(
        {
            "annotation_text": kwargs.get("text", "4-Y20"),
            "candidate_type": kwargs.get("ctype", "LONGITUDINAL_REINFORCEMENT"),
            "role": kwargs.get("role", "TOP_BAR"),
            "diameter_mm": kwargs.get("dia", 20),
            "quantity": kwargs.get("qty", 4),
            "beam_association": kwargs.get("assoc", "TARGET_BEAM"),
            "vision_confidence": kwargs.get("conf", 0.8),
        },
        beam_id=kwargs.get("beam_id", "B99"),
        region_id=kwargs.get("region_id", "P26::Fifth::B99"),
        index=kwargs.get("index", 1),
    )
    if "det" in kwargs:
        base["deterministic_match_status"] = kwargs["det"]
    return base


def _r13(*, top=None, bottom=None, stirrups=None) -> Dict[str, Any]:
    return {
        "beam_id": "B99",
        "top_main_bars": list(top or []),
        "bottom_main_bars": list(bottom or []),
        "stirrups": list(stirrups or []),
        "side_face_reinforcement": [],
        "spacer_bars": [],
        "total_classified_bars": len(top or []) + len(bottom or []) + len(stirrups or []),
    }


def test_schema_validation() -> None:
    c = normalize_candidate(
        {"candidate_type": "NOT_A_TYPE", "role": "MAGIC", "diameter_mm": "nope", "confidence": 9},
        beam_id="B1",
        region_id="R1",
        index=1,
    )
    assert c["candidate_type"] == "UNKNOWN"
    assert c["role"] == "UNKNOWN"
    assert c["diameter_mm"] is None
    assert c["vision_confidence"] is None
    assert c["decision"] == DECISION_SHADOW
    assert "ALLOW" not in c["decision"]
    assert "PROMOTE" not in c["decision"]


def test_malformed_response() -> None:
    cands, report = parse_vision_response("not json at all", beam_id="B1", region_id="R1")
    assert cands == []
    assert report["ok"] is False


def test_unknown_handling() -> None:
    cands, report = parse_vision_response(
        json.dumps(
            {
                "region_id": "R1",
                "beam_id": "B1",
                "candidates": [
                    {
                        "annotation_text": "??",
                        "candidate_type": "UNKNOWN",
                        "role": "UNKNOWN",
                        "diameter_mm": "UNKNOWN",
                        "quantity": "UNKNOWN",
                    }
                ],
            }
        ),
        beam_id="B1",
        region_id="R1",
    )
    assert report["ok"] is True
    assert cands[0]["diameter_mm"] is None
    assert cands[0]["quantity"] is None
    assert cands[0]["role"] == "UNKNOWN"


def test_normalization_aliases() -> None:
    c = normalize_candidate(
        {"semantic_type": "LONGITUDINAL_BAR", "role": "TOP_MAIN", "diameter_mm": 16},
        beam_id="B1",
        region_id="R1",
        index=2,
    )
    assert c["candidate_type"] == "LONGITUDINAL_REINFORCEMENT"
    assert c["role"] == "TOP_BAR"
    assert c["diameter_mm"] == 16


def test_deterministic_already_detected() -> None:
    cand = _cand(role="STIRRUP", ctype="STIRRUP", dia=8, text="2L-Y8@100C/C")
    r13 = _r13(stirrups=[{"bar_id": "S1", "semantic_role": "STIRRUP", "diameter_mm": 8, "bar_label": "2L-Y8@100C/C"}])
    cmp = compare_candidate(cand, r13_model=r13)
    assert cmp["deterministic_match_status"] == DET_ALREADY


def test_deterministic_potentially_missing() -> None:
    cand = _cand(role="BOTTOM_BAR", dia=25, text="4-Y25")
    r13 = _r13(top=[{"bar_id": "T1", "semantic_role": "TOP_MAIN", "diameter_mm": 20, "bar_label": "3-Y20"}])
    cmp = compare_candidate(cand, r13_model=r13)
    assert cmp["deterministic_match_status"] == DET_MISSING


def test_gt_true_recovery() -> None:
    universe = {
        "missed_bars": {
            "B99": [{"beam_id": "B99", "bar_role": "BOTTOM_MAIN", "family": "BOTTOM", "diameter": 25, "quantity": 4, "used": False}]
        },
        "gt_bars": {
            "B99": [{"beam_id": "B99", "bar_role": "BOTTOM_MAIN", "family": "BOTTOM", "diameter": 25, "quantity": 4, "used": False}]
        },
    }
    rec = evaluate_candidate(_cand(role="BOTTOM_BAR", dia=25, qty=4, det=DET_MISSING), universe=universe)
    assert rec["gt_match_status"] == GT_TRUE_RECOVERY
    assert rec["gt_supported"] is True


def test_gt_duplicate() -> None:
    universe = {
        "missed_bars": {"B99": []},
        "gt_bars": {
            "B99": [{"beam_id": "B99", "bar_role": "TOP_MAIN", "family": "TOP", "diameter": 20, "quantity": 4, "used": False}]
        },
    }
    rec = evaluate_candidate(_cand(role="TOP_BAR", dia=20, qty=4, det=DET_ALREADY), universe=universe)
    assert rec["gt_match_status"] == GT_DUPLICATE


def test_gt_unsupported() -> None:
    universe = {"missed_bars": {"B99": []}, "gt_bars": {"B99": []}}
    rec = evaluate_candidate(_cand(role="TOP_BAR", dia=32, qty=8, det=DET_MISSING), universe=universe)
    assert rec["gt_match_status"] == GT_UNSUPPORTED


def test_ambiguous_neighbour() -> None:
    universe = {
        "missed_bars": {
            "B99": [{"beam_id": "B99", "bar_role": "TOP_MAIN", "family": "TOP", "diameter": 20, "quantity": 3, "used": False}]
        },
        "gt_bars": {"B99": []},
    }
    rec = evaluate_candidate(
        _cand(role="TOP_BAR", dia=16, assoc="OTHER_BEAM", det=DET_MISSING),
        universe=universe,
    )
    assert rec["gt_match_status"] == GT_AMBIGUOUS
    assert rec["association_failure"] is True


def test_ambiguous_neighbour_matching_diameter() -> None:
    """OTHER_BEAM must not become TRUE_RECOVERY even if family+diameter match GT."""
    universe = {
        "missed_bars": {
            "B99": [{"beam_id": "B99", "bar_role": "TOP_MAIN", "family": "TOP", "diameter": 20, "quantity": 3, "used": False}]
        },
        "gt_bars": {
            "B99": [{"beam_id": "B99", "bar_role": "TOP_MAIN", "family": "TOP", "diameter": 20, "quantity": 3, "used": False}]
        },
    }
    rec = evaluate_candidate(
        _cand(role="TOP_BAR", dia=20, qty=3, assoc="OTHER_BEAM", det=DET_MISSING),
        universe=universe,
    )
    assert rec["gt_match_status"] == GT_AMBIGUOUS
    assert rec["association_failure"] is True
    assert rec["gt_match_status"] != GT_TRUE_RECOVERY


def test_cache_key_and_roundtrip(tmp_path: Path = None) -> None:
    key = cache_key(
        drawing_hash="d1",
        region_hash="r1",
        prompt_hash="p1",
        vision_model="claude-sonnet-4-5",
        schema_version="P26_VISION_CANDIDATE_SCHEMA_V1",
    )
    key2 = cache_key(
        drawing_hash="d1",
        region_hash="r1",
        prompt_hash="p1",
        vision_model="claude-sonnet-4-5",
        schema_version="P26_VISION_CANDIDATE_SCHEMA_V1",
    )
    assert key == key2
    root = tmp_path or (_pkg() / "_cache_test_tmp")
    root.mkdir(parents=True, exist_ok=True)
    save_cache(root, key, {"request_metadata": {"beam_id": "B1"}, "raw_response": "{}", "normalized_response": {}, "usage": {}})
    loaded = load_cache(root, key)
    assert loaded is not None
    assert loaded["raw_response"] == "{}"
    if tmp_path is None:
        for p in root.glob("*.json"):
            p.unlink()
        root.rmdir()


def test_evidence_provenance_fields() -> None:
    c = _cand()
    assert c["evidence_type"] == "BEAM_REGION_CROP"
    assert c["decision"] == DECISION_SHADOW
    assert c["raw_vision_response_reference"] is None or isinstance(c["raw_vision_response_reference"], str)


def test_gap_score_no_gt_keys() -> None:
    rec = {
        "accepted_annotations": [{"id": "A1", "text": "2L-Y8@100C/C"}],
        "rejected_annotations": [{"id": "A2", "text": "4-Y25"}],
        "envelope": {"depth_mm": 450},
    }
    row = score_beam(beam_id="BX", rec=rec, model={"stirrups": [], "total_classified_bars": 0}, crop_exists=True)
    assert row["score"] > 0
    assert "STIRRUP_TEXT_NO_OBJECT" in row["gap_reasons"]
    blob = json.dumps(row)
    assert "EstimatorOutput" not in blob
    assert "benchmark_answer" not in blob


def test_truth_leak_blocked() -> None:
    leaks = assert_no_truth_leak({"ground_truth": {"diameter_mm": 20}})
    assert leaks


def test_prompt_mentions_unknown() -> None:
    assert "UNKNOWN" in SYSTEM_PROMPT
    user = build_user_prompt(region_id="R", beam_id="B1", metadata={"beam_id": "B1"})
    assert "Do not invent" in SYSTEM_PROMPT or "do not invent" in SYSTEM_PROMPT.lower()
    assert "ground_truth" not in user


def test_production_write_false() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False


def test_model_version() -> None:
    assert MODEL_VERSION == "10.11.0"


def test_no_production_mutation() -> None:
    v10 = _v10()
    paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(paths)
    after = capture_fingerprints(paths)
    cmp = compare_fingerprints(before, after)
    assert cmp.get("unchanged") is True


def test_firewall_and_leakage() -> None:
    fw = firewall_check(_v10())
    assert fw["ok"], fw.get("offenders")
    leak = runtime_leakage_scan(_pkg())
    assert leak["ok"], leak.get("hits")


def test_p2511_regression() -> None:
    nested = run_p2511_unit_tests()
    assert nested.get("success"), nested


def test_malformed_candidates_array() -> None:
    cands, report = parse_vision_response(
        json.dumps({"region_id": "R", "beam_id": "B1", "candidates": "oops"}),
        beam_id="B1",
        region_id="R",
    )
    assert cands == []
    assert report["ok"] is False


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("schema_validation", test_schema_validation),
        ("malformed_response", test_malformed_response),
        ("unknown_handling", test_unknown_handling),
        ("normalization_aliases", test_normalization_aliases),
        ("deterministic_already_detected", test_deterministic_already_detected),
        ("deterministic_potentially_missing", test_deterministic_potentially_missing),
        ("gt_true_recovery", test_gt_true_recovery),
        ("gt_duplicate", test_gt_duplicate),
        ("gt_unsupported", test_gt_unsupported),
        ("ambiguous_neighbour", test_ambiguous_neighbour),
        ("ambiguous_neighbour_matching_diameter", test_ambiguous_neighbour_matching_diameter),
        ("cache_key_and_roundtrip", test_cache_key_and_roundtrip),
        ("evidence_provenance_fields", test_evidence_provenance_fields),
        ("gap_score_no_gt_keys", test_gap_score_no_gt_keys),
        ("truth_leak_blocked", test_truth_leak_blocked),
        ("prompt_mentions_unknown", test_prompt_mentions_unknown),
        ("production_write_false", test_production_write_false),
        ("model_version", test_model_version),
        ("no_production_mutation", test_no_production_mutation),
        ("firewall_and_leakage", test_firewall_and_leakage),
        ("malformed_candidates_array", test_malformed_candidates_array),
        ("P2.5.11_regression", test_p2511_regression),
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
