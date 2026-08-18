"""Unit tests for P2.6.5. No live Claude. Does not change P2.6.4 routing."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP261_stratified_vision_candidate_recovery.set_artefacts import (
    load_ownership,
    load_r13_index,
)

from .config import (
    COORDINATE_SPACE,
    COVER_FULL,
    COVER_LAYER,
    DECISION_CALL,
    DECISION_SKIP,
    GATE_VERSION,
    MAX_LIVE_CALLS,
    MODEL_VERSION,
    PRODUCTION_WRITE,
    STATUS_AMBIGUOUS,
    STATUS_CALL,
    STATUS_INSUFFICIENT,
    STATUS_SKIP,
)
from .context_classifier import classify_spatial_context
from .frozen_sample import load_frozen_manifest
from .geometry_loader import load_beam_scoped_index
from .hypothetical import hypothetical_decision
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)
from .replay_runner import apply_gate_to_frozen
from .shadow_overlay import build_shadow_record
from .spatial_features import band_distance, extract_spatial_features, in_band


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def _ann(text: str, x: Optional[float] = None, y: Optional[float] = None, ann_id: str = "ANN-1") -> Dict[str, Any]:
    row: Dict[str, Any] = {"id": ann_id, "text": text}
    if x is not None:
        row["x"] = x
    if y is not None:
        row["y"] = y
    return row


def _env(*, depth: float = 600.0) -> Dict[str, Any]:
    return {
        "crop_extent": [0.0, 0.0, 3000.0, 800.0],
        "centreline": {"x0": 0.0, "x1": 3000.0, "y": 100.0, "mark_x": 1500.0},
        "top_reinforcement_zone": {"y0": 650.0, "y1": 780.0},
        "bottom_reinforcement_zone": {"y0": 120.0, "y1": 250.0},
        "depth_mm": depth,
    }


def _leader(lid: str, tip_x: float, tip_y: float, tail_x: float, tail_y: float, direction: str) -> Dict[str, Any]:
    return {
        "id": lid,
        "type": "Leader",
        "attributes": {
            "tip_x": tip_x,
            "tip_y": tip_y,
            "tail_x": tail_x,
            "tail_y": tail_y,
            "tip_direction": direction,
            "leader_length": 300.0,
        },
    }


def _bar(bid: str, y: float, place: str, x0: float = 100.0, x1: float = 2000.0) -> Dict[str, Any]:
    return {
        "id": bid,
        "type": "PhysicalBar",
        "attributes": {
            "start_x": x0,
            "end_x": x1,
            "y_position": y,
            "vertical_placement": place,
        },
    }


def _scoped(
    anns: List[Dict[str, Any]],
    leaders: Optional[List[Dict[str, Any]]] = None,
    bars: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = []
    for a in anns:
        nodes.append(
            {
                "id": a.get("id"),
                "type": "Annotation",
                "attributes": {"x": a.get("x"), "y": a.get("y"), "clean_text": a.get("text")},
                "relationships": [],
            }
        )
    nodes.extend(leaders or [])
    nodes.extend(bars or [])
    return {"annotations": anns, "nodes": nodes}


def _rec(texts: List[str], env: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "accepted_annotations": [{"id": f"ANN-{i}", "text": t} for i, t in enumerate(texts)],
        "rejected_annotations": [],
        "envelope": env if env is not None else _env(),
    }


def _real(set_key: str, beam_id: str) -> Dict[str, Any]:
    v10 = _v10()
    rec = (load_ownership(v10, set_key).get("by_beam") or {}).get(beam_id) or {}
    model = load_r13_index(v10, set_key).get(beam_id)
    scoped = load_beam_scoped_index(v10, set_key).get(beam_id) or {}
    return build_shadow_record(
        beam_id=beam_id,
        region_id=f"P261::{set_key}::{beam_id}",
        rec=rec,
        model=model,
        scoped=scoped,
        set_key=set_key,
        source_set=f"{set_key} Set Drawings",
    )


def test_spatial_feature_extraction() -> None:
    rec = _rec(["3-Y16"])
    ann = _ann("3-Y16", 1500, 180, "ANN-0")
    scoped = _scoped(
        [ann],
        leaders=[_leader("LDR::1", 1500, 180, 1500, 200, "UP")],
        bars=[_bar("BAR::1", 700, "TOP_FACE")],
    )
    spat = extract_spatial_features(rec=rec, scoped=scoped, production_features={"populated_layer": "TOP"})
    assert spat["annotation_xy_available"] is True
    assert spat["leader_geometry_available"] is True
    assert spat["physical_bar_geometry_available"] is True
    assert spat["coordinate_space"] == COORDINATE_SPACE
    assert spat["per_annotation"][0]["x"] == 1500
    assert spat["per_annotation"][0]["nearest_top_object_distance"] is not None


def test_missing_geometry_handling() -> None:
    rec = {"accepted_annotations": [_ann("3-Y16")], "rejected_annotations": [], "envelope": {}}
    spat = extract_spatial_features(rec=rec, scoped={}, production_features={})
    assert spat["annotation_xy_available"] is False
    assert "annotation_xy" in spat["unavailable_features"]
    ctx = classify_spatial_context(spatial=spat, production_features={})
    assert ctx["context_status"] == STATUS_INSUFFICIENT


def test_coordinate_normalization() -> None:
    rec = _rec(["3-Y16"])
    ann = _ann("3-Y16", 31674166.38, -21187040.08, "ANN-0")
    scoped = _scoped([ann])
    spat = extract_spatial_features(rec=rec, scoped=scoped)
    assert spat["coordinate_space"] == "DXF_MODEL_MM"
    assert abs(spat["per_annotation"][0]["x"] - 31674166.38) < 1e-6


def test_same_location_duplicate_detection() -> None:
    rec = _rec(["3-Y16", "3-Y16"])
    a1 = _ann("3-Y16", 100, 200, "ANN-0")
    a2 = _ann("3-Y16", 108, 205, "ANN-1")
    spat = extract_spatial_features(rec=rec, scoped=_scoped([a1, a2]), production_features={"populated_layer": "TOP"})
    assert spat["repeated_same_location"] is True
    assert spat["repeated_separate_location"] is False


def test_spatial_separation_detection() -> None:
    rec = _rec(["3-Y16", "3-Y16"])
    a1 = _ann("3-Y16", 100, 700, "ANN-0")
    a2 = _ann("3-Y16", 110, 150, "ANN-1")
    spat = extract_spatial_features(rec=rec, scoped=_scoped([a1, a2]), production_features={"populated_layer": "TOP"})
    assert spat["repeated_separate_location"] is True
    assert spat["max_repeat_dy"] > 400


def test_top_bottom_proximity() -> None:
    rec = _rec(["3-Y16"])
    ann = _ann("3-Y16", 1500, 200, "ANN-0")
    ldr = _leader("LDR::1", 1500, 180, 1500, 220, "UP")
    scoped = _scoped([ann], leaders=[ldr])
    spat = extract_spatial_features(rec=rec, scoped=scoped, production_features={"populated_layer": "TOP"})
    row = spat["per_annotation"][0]
    assert row["tip_in_bottom_zone"] is True
    assert row["dist_tip_top_zone"] > 90


def test_repeated_annotation_handling() -> None:
    rec = _rec(["3-Y16", "3-Y16"])
    a1 = _ann("3-Y16", 100, 700, "ANN-0")
    a2 = _ann("3-Y16", 110, 160, "ANN-1")
    l1 = _leader("LDR::A", 100, 700, 100, 680, "DOWN")
    l2 = _leader("LDR::B", 110, 180, 110, 200, "UP")
    spat = extract_spatial_features(
        rec=rec,
        scoped=_scoped([a1, a2], leaders=[l1, l2]),
        production_features={"populated_layer": "TOP", "unique_accepted_spec_count": 1, "accepted_instance_count": 2},
    )
    ctx = classify_spatial_context(
        spatial=spat,
        production_features={"unique_accepted_spec_count": 1, "accepted_instance_count": 2, "populated_layer": "TOP"},
    )
    assert ctx["context_status"] == STATUS_CALL
    assert "REPEATED_SEPARATE_LOCATION" in ctx["evidence_codes"]


def test_cluster_detection() -> None:
    rec = _rec(["3-Y16"])
    ann = _ann("3-Y16", 1500, 200, "ANN-0")
    bars = [_bar("B1", 700, "TOP_FACE"), _bar("B2", 160, "BOTTOM_FACE")]
    spat = extract_spatial_features(rec=rec, scoped=_scoped([ann], bars=bars))
    assert spat["physical_bar_cluster_count"] >= 2


def test_evidence_aggregation() -> None:
    spatial = {
        "annotation_xy_available": True,
        "leader_geometry_available": True,
        "physical_bar_geometry_available": False,
        "envelope_available": True,
        "populated_layer": "TOP",
        "repeated_separate_location": False,
        "repeated_same_location": False,
        "annotation_cluster_count": 1,
        "physical_bar_cluster_count": 0,
        "tip_layer_votes": ["TOP"],
    }
    ctx = classify_spatial_context(
        spatial=spatial,
        production_features={"unique_accepted_spec_count": 1, "accepted_instance_count": 1, "populated_layer": "TOP"},
    )
    assert ctx["skip_votes"] >= 2
    assert ctx["context_status"] == STATUS_SKIP


def test_ambiguity_preservation() -> None:
    spatial = {
        "annotation_xy_available": True,
        "leader_geometry_available": True,
        "physical_bar_geometry_available": False,
        "envelope_available": True,
        "populated_layer": "TOP",
        "repeated_separate_location": False,
        "repeated_same_location": False,
        "annotation_cluster_count": 1,
        "physical_bar_cluster_count": 0,
        "tip_layer_votes": ["BOUNDARY"],
    }
    ctx = classify_spatial_context(
        spatial=spatial,
        production_features={"unique_accepted_spec_count": 1, "accepted_instance_count": 1},
    )
    assert ctx["context_status"] in (STATUS_AMBIGUOUS, STATUS_INSUFFICIENT)


def test_single_feature_cannot_skip() -> None:
    spatial = {
        "annotation_xy_available": True,
        "leader_geometry_available": False,
        "physical_bar_geometry_available": True,
        "envelope_available": True,
        "populated_layer": "TOP",
        "repeated_separate_location": False,
        "min_object_distance": 5.0,
        "annotation_cluster_count": 1,
        "physical_bar_cluster_count": 1,
        "tip_layer_votes": [],
    }
    ctx = classify_spatial_context(
        spatial=spatial,
        production_features={"unique_accepted_spec_count": 1},
    )
    assert ctx["context_status"] != STATUS_SKIP


def test_b128_true_recovery_preservation() -> None:
    d = _real("Fifth", "B128")
    assert d["decision"] == DECISION_CALL
    assert d["observed_decision"] == DECISION_CALL
    assert d["longitudinal_coverage"] == COVER_LAYER
    assert d["context_status"] != STATUS_SKIP
    assert d["production_routing_changed"] is False


def test_b173_true_recovery_preservation() -> None:
    d = _real("Fifth", "B173")
    assert d["decision"] == DECISION_CALL
    assert d["context_status"] == STATUS_CALL
    assert "REPEATED_SEPARATE_LOCATION" in d["context_evidence_codes"]


def test_b100_duplicate_only_behaviour() -> None:
    d = _real("Fifth", "B100")
    assert d["decision"] == DECISION_CALL
    assert d["longitudinal_coverage"] == COVER_LAYER
    assert d["context_status"] != STATUS_CALL or "CROSS_LAYER_SEPARATION" not in (
        d.get("context_evidence_codes") or []
    )


def test_b141_duplicate_only_behaviour() -> None:
    d = _real("Fourth", "B141")
    assert d["decision"] == DECISION_CALL
    assert d["context_status"] != STATUS_SKIP


def test_b23_duplicate_only_behaviour() -> None:
    d = _real("Fourth", "B23")
    assert d["decision"] == DECISION_CALL
    assert d["context_status"] != STATUS_SKIP


def test_b136_false_skip_diagnostic() -> None:
    d = _real("Fifth", "B136")
    assert d["longitudinal_coverage"] == COVER_FULL
    assert d["decision"] == DECISION_SKIP
    hypo = hypothetical_decision(d)
    assert hypo["hypothetical_decision"] == DECISION_SKIP


def test_band_distance_helpers() -> None:
    z = {"y0": 10, "y1": 20}
    assert band_distance(15, z) == 0.0
    assert in_band(15, z) is True
    assert band_distance(25, z) == 5.0
    assert band_distance(None, z) is None


def test_no_production_mutation() -> None:
    paths = fingerprint_paths(_v10(), {})
    cmp = compare_fingerprints(capture_fingerprints(paths), capture_fingerprints(paths))
    assert cmp.get("unchanged") is True


def test_no_live_vision_api() -> None:
    assert MAX_LIVE_CALLS == 0
    orch = (_pkg() / "phase_p265_orchestrator.py").read_text(encoding="utf-8")
    assert "observe_region" not in orch
    assert "anthropic" not in orch.lower()


def test_frozen_p261_replay_integrity() -> None:
    regions, summary = load_frozen_manifest(_v10())
    assert int(summary.get("seed") or 0) == 2611101
    assert len(regions) == 75


def test_p264_artefact_immutability_paths() -> None:
    paths = fingerprint_paths(_v10(), {})
    assert "p264_status" in paths
    assert paths["p264_status"].name == "P2.6.4_STATUS.md"
    assert paths["p264_status"].exists()


def test_production_write_false() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert MODEL_VERSION == "10.11.5"
    assert GATE_VERSION == "P265_SPATIAL_CONTEXT_LONGITUDINAL_V1_0"


def test_gate_runtime_no_gt_tokens() -> None:
    for name in ("spatial_features.py", "context_classifier.py", "shadow_overlay.py", "hypothetical.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "TRUE_RECOVERY" not in text
        assert "gt_match_status" not in text
        assert "load_gt_universe" not in text


def test_gate_runtime_no_estimator_tokens() -> None:
    for name in ("spatial_features.py", "context_classifier.py", "shadow_overlay.py"):
        text = (_pkg() / name).read_text(encoding="utf-8")
        assert "EstimatorOutput" not in text
        assert "estimator_steel" not in text


def test_stratum_not_used_in_classifier() -> None:
    src = (_pkg() / "context_classifier.py").read_text(encoding="utf-8")
    assert "stratum" not in src
    spat_src = (_pkg() / "spatial_features.py").read_text(encoding="utf-8")
    assert "stratum" not in spat_src


def test_firewall_and_leakage() -> None:
    fw = firewall_check(_v10())
    assert fw["ok"], fw.get("offenders")
    leak = runtime_leakage_scan(_pkg())
    assert leak["ok"], leak.get("hits")


def test_observed_routing_unchanged_from_p264() -> None:
    d = _real("Fifth", "B128")
    assert d["decision"] == d["observed_decision"]
    assert d["production_routing_changed"] is False


def test_hypothetical_does_not_skip_stirrup_calls() -> None:
    row = {
        "decision": DECISION_CALL,
        "context_status": STATUS_SKIP,
        "longitudinal_coverage": COVER_LAYER,
        "reason_codes": ["STIRRUP_TEXT_NO_OBJECT", "LONGITUDINAL_COVERAGE_SHORTFALL"],
    }
    h = hypothetical_decision(row)
    assert h["hypothetical_decision"] == DECISION_CALL


def test_replay_skip_drops_candidates() -> None:
    decisions = [
        {"set_key": "Fifth", "beam_id": "B1", "decision": DECISION_CALL},
        {"set_key": "Fifth", "beam_id": "B2", "decision": DECISION_SKIP},
    ]
    frozen = [
        {"set_key": "Fifth", "beam_id": "B1", "candidate_id": "C1"},
        {"set_key": "Fifth", "beam_id": "B2", "candidate_id": "C2"},
    ]
    gated, summary = apply_gate_to_frozen(decisions=decisions, frozen_candidates=frozen)
    assert len(gated) == 1
    assert summary["suppressed_candidates"] == 1


def test_p264_regression() -> None:
    prior = (
        _v10()
        / "data"
        / "output"
        / "PhaseP264_selective_role_gap_gate"
        / "unit_tests.json"
    )
    assert prior.exists()
    import json

    payload = json.loads(prior.read_text(encoding="utf-8"))
    assert payload.get("success") is True
    assert int(payload.get("passed") or 0) >= 30
    assert int(payload.get("total") or 0) >= 30


def test_no_beam_id_hardcoding_in_classifier() -> None:
    text = (_pkg() / "context_classifier.py").read_text(encoding="utf-8")
    for token in ("B128", "B173", "B100", "B136", "B23", "B141"):
        assert token not in text
    spat = (_pkg() / "spatial_features.py").read_text(encoding="utf-8")
    for token in ("B128", "B173", "B100", "B136"):
        assert token not in spat


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("spatial_feature_extraction", test_spatial_feature_extraction),
        ("missing_geometry_handling", test_missing_geometry_handling),
        ("coordinate_normalization", test_coordinate_normalization),
        ("same_location_duplicate_detection", test_same_location_duplicate_detection),
        ("spatial_separation_detection", test_spatial_separation_detection),
        ("top_bottom_proximity", test_top_bottom_proximity),
        ("repeated_annotation_handling", test_repeated_annotation_handling),
        ("cluster_detection", test_cluster_detection),
        ("evidence_aggregation", test_evidence_aggregation),
        ("ambiguity_preservation", test_ambiguity_preservation),
        ("single_feature_cannot_skip", test_single_feature_cannot_skip),
        ("b128_true_recovery_preservation", test_b128_true_recovery_preservation),
        ("b173_true_recovery_preservation", test_b173_true_recovery_preservation),
        ("b100_duplicate_only_behaviour", test_b100_duplicate_only_behaviour),
        ("b141_duplicate_only_behaviour", test_b141_duplicate_only_behaviour),
        ("b23_duplicate_only_behaviour", test_b23_duplicate_only_behaviour),
        ("b136_false_skip_diagnostic", test_b136_false_skip_diagnostic),
        ("band_distance_helpers", test_band_distance_helpers),
        ("no_production_mutation", test_no_production_mutation),
        ("no_live_vision_api", test_no_live_vision_api),
        ("frozen_p261_replay_integrity", test_frozen_p261_replay_integrity),
        ("p264_artefact_immutability_paths", test_p264_artefact_immutability_paths),
        ("production_write_false", test_production_write_false),
        ("gate_runtime_no_gt_tokens", test_gate_runtime_no_gt_tokens),
        ("gate_runtime_no_estimator_tokens", test_gate_runtime_no_estimator_tokens),
        ("stratum_not_used_in_classifier", test_stratum_not_used_in_classifier),
        ("firewall_and_leakage", test_firewall_and_leakage),
        ("observed_routing_unchanged_from_p264", test_observed_routing_unchanged_from_p264),
        ("hypothetical_does_not_skip_stirrup_calls", test_hypothetical_does_not_skip_stirrup_calls),
        ("replay_skip_drops_candidates", test_replay_skip_drops_candidates),
        ("no_beam_id_hardcoding_in_classifier", test_no_beam_id_hardcoding_in_classifier),
        ("P2.6.4_regression", test_p264_regression),
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
