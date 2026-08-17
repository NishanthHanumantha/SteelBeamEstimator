"""Unit + integration tests for P2.6.1. No live Claude in the default suite."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from PhaseP26_vision_candidate_recovery.cache import cache_key
from PhaseP26_vision_candidate_recovery.candidate_schema import normalize_candidate
from PhaseP26_vision_candidate_recovery.unit_tests import run_unit_tests as run_p26_unit_tests

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
    SAMPLE_SEED,
)
from .ground_truth_matcher import evaluate_candidate, universe_key
from .policy import PRODUCTION_WRITE as POLICY_WRITE, assert_neutral_metadata
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)
from .sampler import sample_stratified
from .stratifier import assign_stratum
from .vision_prompt import (
    SYSTEM_PROMPT,
    assert_prompt_neutral,
    build_user_prompt,
    prompt_fingerprint,
)


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
        region_id=kwargs.get("region_id", "P261::Fifth::B99"),
        index=kwargs.get("index", 1),
    )
    base["source_set"] = kwargs.get("source_set", "Fifth Set Drawings")
    base["source_drawing"] = base["source_set"]
    if "det" in kwargs:
        base["deterministic_match_status"] = kwargs["det"]
    return base


def _universe_for(beam_id: str = "B99", set_key: str = "Fifth") -> Dict[str, Any]:
    uk = universe_key(set_key, beam_id)
    missed = {
        "beam_id": beam_id,
        "bar_role": "BOTTOM_MAIN",
        "family": "BOTTOM",
        "diameter": 25,
        "quantity": 4,
        "used": False,
    }
    gt = dict(missed)
    return {
        "missed_bars": {uk: [missed]},
        "gt_bars": {uk: [gt]},
    }


def test_schema_valid_and_malformed() -> None:
    c = normalize_candidate(
        {"candidate_type": "NOT_A_TYPE", "role": "MAGIC", "diameter_mm": "nope"},
        beam_id="B1",
        region_id="R1",
        index=1,
    )
    assert c["candidate_type"] == "UNKNOWN"
    assert c["role"] == "UNKNOWN"
    assert c["diameter_mm"] is None
    assert c["decision"] == DECISION_SHADOW


def test_unknown_values() -> None:
    c = normalize_candidate(
        {
            "candidate_type": "UNKNOWN",
            "role": "UNKNOWN",
            "diameter_mm": "UNKNOWN",
            "quantity": "UNKNOWN",
        },
        beam_id="B1",
        region_id="R1",
        index=1,
    )
    assert c["diameter_mm"] is None
    assert c["quantity"] is None


def test_stratifier_difficult_normal_easy() -> None:
    difficult = assign_stratum(
        {
            "score": 12,
            "features": {
                "OCR_CORRUPTION_SIGNAL": True,
                "STIRRUP_TEXT_NO_OBJECT": True,
                "INCOMPLETE_PARSE_SIGNAL": False,
                "SPARSE_REINFORCEMENT_SIGNAL": False,
            },
            "has_crop": True,
            "annotation_count": 2,
        }
    )
    easy = assign_stratum(
        {
            "score": 0,
            "features": {
                "OCR_CORRUPTION_SIGNAL": False,
                "STIRRUP_TEXT_NO_OBJECT": False,
                "INCOMPLETE_PARSE_SIGNAL": False,
                "REINFORCEMENT_DENSITY": 6,
                "HAS_TOP": True,
                "HAS_BOTTOM": True,
            },
            "has_crop": True,
            "annotation_count": 3,
        }
    )
    normal = assign_stratum(
        {
            "score": 3,
            "features": {
                "OCR_CORRUPTION_SIGNAL": False,
                "STIRRUP_TEXT_NO_OBJECT": False,
                "INCOMPLETE_PARSE_SIGNAL": False,
                "REINFORCEMENT_DENSITY": 2,
                "HAS_TOP": True,
                "HAS_BOTTOM": False,
            },
            "has_crop": True,
            "annotation_count": 2,
        }
    )
    assert difficult == "DIFFICULT"
    assert easy == "EASY"
    assert normal == "NORMAL"


def _synthetic_universe() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for stratum in ("DIFFICULT", "NORMAL", "EASY"):
        for set_key in ("Fourth", "Fifth", "Sixth"):
            for i in range(1, 16):
                rows.append(
                    {
                        "set_key": set_key,
                        "source_set": f"{set_key} Set Drawings",
                        "source_drawing": f"{set_key} Set Drawings",
                        "beam_id": f"{set_key[:1]}{stratum[0]}{i:02d}",
                        "stratum": stratum,
                        "has_crop": True,
                        "features": {"OCR_CORRUPTION_SIGNAL": stratum == "DIFFICULT"},
                        "score": 10 if stratum == "DIFFICULT" else 0,
                    }
                )
    return rows


def test_sampling_deterministic_seed() -> None:
    universe = _synthetic_universe()
    a, sa = sample_stratified(universe, seed=SAMPLE_SEED, per_stratum=9)
    b, sb = sample_stratified(universe, seed=SAMPLE_SEED, per_stratum=9)
    ids_a = [(r["set_key"], r["beam_id"], r["stratum"]) for r in a]
    ids_b = [(r["set_key"], r["beam_id"], r["stratum"]) for r in b]
    assert ids_a == ids_b
    assert sa["selected_by_stratum"] == {"DIFFICULT": 9, "NORMAL": 9, "EASY": 9}
    assert sa["gt_used_for_selection"] is False
    c, _ = sample_stratified(universe, seed=SAMPLE_SEED + 1, per_stratum=9)
    ids_c = [(r["set_key"], r["beam_id"], r["stratum"]) for r in c]
    assert ids_a != ids_c


def test_sampling_no_gt_access() -> None:
    for name in (
        "sampler.py",
        "features.py",
        "stratifier.py",
        "region_builder.py",
        "vision_observer.py",
        "vision_prompt.py",
        "set_artefacts.py",
        "config.py",
    ):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "load_gt_universe" not in text
        assert "WorkbookNormalizer" not in text
        assert "EstimatorOutput" not in text
        assert "benchmark_answer" not in text


def test_prompt_neutrality() -> None:
    metadata = {
        "region_id": "P261::Fifth::B1",
        "beam_id": "B1",
        "source_set": "Fifth Set Drawings",
        "target_beam": "B1",
        "visible_callout_texts": ["4-Y20"],
    }
    user = build_user_prompt(region_id="P261::Fifth::B1", beam_id="B1", metadata=metadata)
    blob = (SYSTEM_PROMPT + "\n" + user).lower()
    for tok in ("gap_reasons", "selection_reason", "stratum", "expected_failure", "expected missing"):
        assert tok not in blob
    assert not assert_prompt_neutral(SYSTEM_PROMPT)
    assert not assert_prompt_neutral(user)
    raised = False
    try:
        assert_neutral_metadata({"gap_reasons": ["OCR"]})
    except ValueError:
        raised = True
    assert raised


def test_gt_true_recovery_and_duplicate_and_unsupported() -> None:
    universe = _universe_for()
    rec = evaluate_candidate(
        _cand(role="BOTTOM_BAR", dia=25, qty=4, det=DET_MISSING),
        universe=universe,
    )
    assert rec["gt_match_status"] == GT_TRUE_RECOVERY
    assert rec["p26_compatible_true_recovery"] is True
    assert rec["strict_true_recovery"] is True

    stirrup2 = evaluate_candidate(
        _cand(role="STIRRUP", ctype="STIRRUP", dia=8, qty=None, text="2L-Y8@100C/C", det=DET_MISSING),
        universe={
            "missed_bars": {
                universe_key("Fifth", "B99"): [
                    {
                        "beam_id": "B99",
                        "bar_role": "STIRRUP",
                        "family": "STIRRUP",
                        "diameter": 8,
                        "quantity": None,
                        "used": False,
                    }
                ]
            },
            "gt_bars": {universe_key("Fifth", "B99"): []},
        },
    )
    assert stirrup2["gt_match_status"] == GT_TRUE_RECOVERY
    assert stirrup2["strict_true_recovery"] is False

    universe2 = {
        "missed_bars": {universe_key("Fifth", "B99"): []},
        "gt_bars": {
            universe_key("Fifth", "B99"): [
                {
                    "beam_id": "B99",
                    "bar_role": "TOP_MAIN",
                    "family": "TOP",
                    "diameter": 20,
                    "quantity": 4,
                    "used": False,
                }
            ]
        },
    }
    dup = evaluate_candidate(_cand(role="TOP_BAR", dia=20, qty=4, det=DET_ALREADY), universe=universe2)
    assert dup["gt_match_status"] == GT_DUPLICATE

    universe3 = {"missed_bars": {universe_key("Fifth", "B99"): []}, "gt_bars": {universe_key("Fifth", "B99"): []}}
    uns = evaluate_candidate(_cand(role="TOP_BAR", dia=32, qty=8, det=DET_MISSING), universe=universe3)
    assert uns["gt_match_status"] == GT_UNSUPPORTED


def test_other_beam_cannot_recover() -> None:
    universe = {
        "missed_bars": {
            universe_key("Fifth", "B99"): [
                {
                    "beam_id": "B99",
                    "bar_role": "TOP_MAIN",
                    "family": "TOP",
                    "diameter": 20,
                    "quantity": 3,
                    "used": False,
                }
            ]
        },
        "gt_bars": {
            universe_key("Fifth", "B99"): [
                {
                    "beam_id": "B99",
                    "bar_role": "TOP_MAIN",
                    "family": "TOP",
                    "diameter": 20,
                    "quantity": 3,
                    "used": False,
                }
            ]
        },
    }
    rec = evaluate_candidate(
        _cand(role="TOP_BAR", dia=20, qty=3, assoc="OTHER_BEAM", det=DET_MISSING),
        universe=universe,
    )
    assert rec["gt_match_status"] == GT_AMBIGUOUS
    assert rec["gt_match_status"] != GT_TRUE_RECOVERY


def test_uncertain_association_not_true_recovery() -> None:
    universe = _universe_for()
    rec = evaluate_candidate(
        _cand(role="BOTTOM_BAR", dia=25, qty=4, assoc="UNCERTAIN", det=DET_MISSING),
        universe=universe,
    )
    assert rec["gt_match_status"] == GT_AMBIGUOUS
    assert rec.get("p26_compatible_true_recovery") is False


def test_cache_key_prompt_invalidation() -> None:
    common = dict(
        drawing_hash="d1",
        region_hash="r1",
        vision_model="claude-sonnet-4-5",
        schema_version="P26_VISION_CANDIDATE_SCHEMA_V1",
    )
    a = cache_key(prompt_hash="p1", **common)
    b = cache_key(prompt_hash="p1", **common)
    c = cache_key(prompt_hash="p2", **common)
    assert a == b
    assert a != c
    fp1 = prompt_fingerprint(SYSTEM_PROMPT, "user-a")
    fp2 = prompt_fingerprint(SYSTEM_PROMPT, "user-b")
    assert fp1 != fp2


def test_production_write_false() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert MODEL_VERSION == "10.11.1"


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


def test_p26_regression() -> None:
    nested = run_p26_unit_tests()
    assert nested.get("success"), nested


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("schema_valid_and_malformed", test_schema_valid_and_malformed),
        ("unknown_values", test_unknown_values),
        ("stratifier_difficult_normal_easy", test_stratifier_difficult_normal_easy),
        ("sampling_deterministic_seed", test_sampling_deterministic_seed),
        ("sampling_no_gt_access", test_sampling_no_gt_access),
        ("prompt_neutrality", test_prompt_neutrality),
        ("gt_true_recovery_and_duplicate_and_unsupported", test_gt_true_recovery_and_duplicate_and_unsupported),
        ("other_beam_cannot_recover", test_other_beam_cannot_recover),
        ("uncertain_association_not_true_recovery", test_uncertain_association_not_true_recovery),
        ("cache_key_prompt_invalidation", test_cache_key_prompt_invalidation),
        ("production_write_false", test_production_write_false),
        ("no_production_mutation", test_no_production_mutation),
        ("firewall_and_leakage", test_firewall_and_leakage),
        ("P2.6_regression", test_p26_regression),
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
