"""Unit tests for P2.6.10-D.1. Offline. No production mutation. No Claude."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .anti_hardcoding import ordering_invariance, rename_invariance, run_anti_hardcoding, source_guard
from .config import (
    AUTH_DET_ENG,
    AUTH_VISION,
    GATE_VERSION,
    LIVE_CLAUDE_CALL,
    MODEL_VERSION,
    PRODUCTION_WRITE,
    REASON_ACCEPTED,
    REASON_DET_ONLY,
    REASON_INCONSISTENT,
    REASON_LOW_CONF,
    REASON_VISION_ONLY,
    VISION_MIN_CONFIDENCE,
)
from .discovery import dedupe_observations, is_live_vision_observation
from .hybrid_authority_contract import DETERMINISTIC_AUTHORITY_FIELDS, VISION_PREFERRED_FIELDS, field_authority, is_vision_preferred
from .normalize import parse_bar_count, parse_diameter
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    prior_artefacts_intact,
    prior_phase_unit_ok,
    runtime_leakage_scan,
)
from .resolver import resolve_beam, resolve_group
from .vision_normalizer import extract_deterministic_groups, extract_vision_payload
from .vision_validator import flag_possible_duplicates, validate_field


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def _vis_group(**kwargs: Any) -> Dict[str, Any]:
    rec = {
        "layer": "TOP",
        "role_hypothesis": "MAIN",
        "spec": "5-Y20",
        "bar_count": 5,
        "confidence": 0.95,
        "role_confidence": 0.9,
        "support_scope": "FULL_SPAN",
    }
    rec.update(kwargs)
    return rec


def _det_group(**kwargs: Any) -> Dict[str, Any]:
    rec = {
        "family": "LONGITUDINAL",
        "physical_layer": "TOP",
        "reinforcement_role": "MAIN",
        "specification": "5Y16",
        "count": 5,
        "diameter": 16,
        "zone": "FULL_SPAN",
        "cut_length_mm": 8000,
    }
    rec.update(kwargs)
    return rec


def _resolve(vision_groups: List[Dict[str, Any]], det_groups: List[Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
    vis = extract_vision_payload(
        {
            "usable": kwargs.get("usable", True),
            "target_beam_id": kwargs.get("tid", "T01"),
            "target_identified": kwargs.get("identified", True),
            "association_confidence": kwargs.get("tconf", 0.95),
            "groups": vision_groups,
            "stirrups": kwargs.get("stirrups") or [],
        }
    )
    det = extract_deterministic_groups(det_groups)
    return resolve_beam(beam_id=kwargs.get("beam_id", "T01"), vision=vis, deterministic=det, source_provenance={})


def test_a_valid_vision_accepted() -> None:
    out = _resolve([_vis_group()], [_det_group()])
    g = out["groups"][0]
    assert g["layer"]["reason"] == REASON_ACCEPTED
    assert g["layer"]["resolved_value"] == "TOP"


def test_b_low_confidence_rejected() -> None:
    out = _resolve([_vis_group(confidence=0.2, role_confidence=0.2)], [_det_group()])
    g = out["groups"][0]
    assert g["diameter"]["reason"] == REASON_LOW_CONF
    assert g["diameter"]["resolved_value"] == 16
    assert g["diameter"]["authority_used"].startswith("DETERMINISTIC")


def test_c_invalid_bar_count() -> None:
    rec = validate_field(field="BAR_COUNT", vision_value=0, confidence=0.9, spec="5-Y20")
    assert rec["accepted"] is False
    rec2 = validate_field(field="BAR_COUNT", vision_value=-3, confidence=0.9, spec="3-Y16")
    assert rec2["accepted"] is False
    out = _resolve([_vis_group(bar_count=0, spec="5-Y20")], [_det_group(count=5)])
    assert out["groups"][0]["bar_count"]["resolved_value"] == 5


def test_d_invalid_diameter() -> None:
    rec = validate_field(field="DIAMETER", vision_value=99, confidence=0.9, spec="5-Y99")
    assert rec["accepted"] is False
    out = _resolve([_vis_group(spec="5-Y99", bar_count=5)], [_det_group(diameter=16, specification="5Y16")])
    assert out["groups"][0]["diameter"]["resolved_value"] == 16


def test_e_spec_count_inconsistent() -> None:
    rec = validate_field(field="BAR_COUNT", vision_value=4, confidence=0.9, spec="5-Y20")
    assert rec["accepted"] is False
    assert rec["reason"] == REASON_INCONSISTENT
    rec2 = validate_field(field="SPECIFICATION", vision_value="5-Y20", confidence=0.9, bar_count=4, diameter=20)
    assert rec2["accepted"] is False


def test_f_spec_diameter_inconsistent() -> None:
    rec = validate_field(field="DIAMETER", vision_value=16, confidence=0.9, spec="5-Y20")
    assert rec["accepted"] is False
    assert rec["reason"] == REASON_INCONSISTENT
    rec2 = validate_field(field="SPECIFICATION", vision_value="5-Y20", confidence=0.9, bar_count=5, diameter=16)
    assert rec2["accepted"] is False


def test_g_vision_layer_preferred() -> None:
    out = _resolve([_vis_group(layer="BOTTOM")], [_det_group(physical_layer="TOP")])
    g = out["groups"][0]
    assert g["layer"]["resolved_value"] == "BOTTOM"
    assert g["layer"]["authority_used"] == AUTH_VISION
    assert g["layer"]["deterministic_value"] == "TOP"


def test_h_vision_count_preferred() -> None:
    out = _resolve([_vis_group(spec="3-Y20", bar_count=3)], [_det_group(count=5, specification="5Y20", diameter=20)])
    g = out["groups"][0]
    assert g["bar_count"]["resolved_value"] == 3
    assert g["bar_count"]["authority_used"] == AUTH_VISION


def test_i_vision_diameter_overrides_det() -> None:
    assert is_vision_preferred("DIAMETER")
    out = _resolve([_vis_group(spec="5-Y20", bar_count=5)], [_det_group(diameter=16, specification="5Y16", count=5)])
    g = out["groups"][0]
    assert g["diameter"]["vision_value"] == 20
    assert g["diameter"]["deterministic_value"] == 16
    assert g["diameter"]["resolved_value"] == 20
    assert g["diameter"]["authority_used"] == AUTH_VISION
    assert g["diameter"]["conflict_recorded"] is True


def test_j_vision_spec_preferred() -> None:
    out = _resolve([_vis_group(spec="5-Y20")], [_det_group(specification="5Y16")])
    g = out["groups"][0]
    assert g["specification"]["resolved_value"] == "5-Y20"
    assert g["specification"]["authority_used"] == AUTH_VISION


def test_k_vision_role_overrides_det() -> None:
    assert is_vision_preferred("ROLE")
    out = _resolve([_vis_group(role_hypothesis="EXTRA")], [_det_group(reinforcement_role="MAIN")])
    g = out["groups"][0]
    assert g["role"]["vision_value"] == "EXTRA"
    assert g["role"]["deterministic_value"] == "MAIN"
    assert g["role"]["resolved_value"] == "EXTRA"
    assert g["role"]["authority_used"] == AUTH_VISION
    assert g["role"]["conflict_recorded"] is True


def test_l_role_fallback_when_invalid() -> None:
    out = _resolve([_vis_group(role_hypothesis="NOT_A_ROLE")], [_det_group(reinforcement_role="MAIN")])
    g = out["groups"][0]
    assert g["role"]["resolved_value"] == "MAIN"
    assert g["role"]["authority_used"].startswith("DETERMINISTIC")


def test_m_diameter_fallback_when_invalid() -> None:
    vis = extract_vision_payload(
        {
            "usable": True,
            "target_beam_id": "T01",
            "target_identified": True,
            "association_confidence": 0.95,
            "groups": [{"layer": "TOP", "role": "MAIN", "spec": "5-Y20", "bar_count": 5, "diameter": 99, "confidence": 0.95}],
            "stirrups": [],
        }
    )
    vis["groups"][0]["diameter"] = 99
    vis["groups"][0]["specification"] = "5-Y99"
    det = extract_deterministic_groups([_det_group(diameter=16, specification="5Y16")])
    out = resolve_beam(beam_id="T01", vision=vis, deterministic=det, source_provenance={})
    assert out["groups"][0]["diameter"]["resolved_value"] == 16


def test_n_same_spec_remain_distinct() -> None:
    out = _resolve(
        [
            _vis_group(physical_group_id="G1", layer="TOP", role_hypothesis="MAIN", spec="3-Y20", bar_count=3),
            _vis_group(physical_group_id="G2", layer="TOP", role_hypothesis="EXTRA", spec="3-Y20", bar_count=3, support_scope="LEFT_SUPPORT"),
        ],
        [
            _det_group(group_id="D1", reinforcement_role="MAIN", specification="3Y20", count=3, diameter=20),
            _det_group(group_id="D2", reinforcement_role="EXTRA", specification="3Y20", count=3, diameter=20, zone="LEFT_SUPPORT"),
        ],
    )
    assert len(out["groups"]) == 2
    roles = sorted(g["role"]["resolved_value"] for g in out["groups"])
    assert roles == ["EXTRA", "MAIN"]


def test_o_vision_only_preserved() -> None:
    out = _resolve(
        [_vis_group(), _vis_group(layer="BOTTOM", spec="3-Y16", bar_count=3, role_hypothesis="MAIN")],
        [_det_group()],
    )
    origins = [g["origin"] for g in out["groups"]]
    assert REASON_VISION_ONLY in origins
    assert out["resolution_summary"]["vision_only_groups"] >= 1


def test_p_deterministic_only_preserved() -> None:
    out = _resolve(
        [_vis_group()],
        [_det_group(), _det_group(physical_layer="BOTTOM", specification="3Y12", count=3, diameter=12)],
    )
    origins = [g["origin"] for g in out["groups"]]
    assert REASON_DET_ONLY in origins
    assert out["resolution_summary"]["deterministic_only_groups"] >= 1


def test_q_stirrup_id_split_from_engineering() -> None:
    out = _resolve(
        [_vis_group()],
        [_det_group(), {"family": "STIRRUP", "physical_layer": "STIRRUP", "reinforcement_role": "STIRRUP", "specification": "3L-Y10", "count": 3, "diameter": 10, "cut_length_mm": 3100}],
        stirrups=[{"spec": "4L-Y8@100C/C", "confidence": 0.9}],
    )
    assert out["stirrups"]
    s = out["stirrups"][0]
    assert s["identification"]["resolved_value"] in ("4L-Y8@100C/C", "3L-Y10")
    assert s["engineering_calculation_authority"] == AUTH_DET_ENG
    assert is_vision_preferred("STIRRUP_IDENTIFICATION")
    assert field_authority("STIRRUP_ENGINEERING_CALCULATION") == AUTH_DET_ENG


def test_r_spacer_deterministic() -> None:
    assert not is_vision_preferred("SPACER")
    out = _resolve(
        [_vis_group()],
        [_det_group(), {"family": "SPACER", "physical_layer": "SPACER", "reinforcement_role": "SPACER", "specification": "2Y12", "count": 2, "diameter": 12}],
    )
    assert len(out["spacers"]["groups"]) == 1
    assert out["spacers"]["authority"] == AUTH_DET_ENG


def test_s_cut_length_deterministic() -> None:
    assert not is_vision_preferred("CUT_LENGTH")
    out = _resolve([_vis_group()], [_det_group(cut_length_mm=8416.8)])
    assert out["deterministic_engineering_data"]["authority"] == AUTH_DET_ENG
    assert out["groups"][0]["provenance"]["deterministic_cut_length_mm"] == 8416.8


def test_t_group_ordering_invariance() -> None:
    assert ordering_invariance().get("ok") is True


def test_u_input_ordering_invariance() -> None:
    a = _resolve(
        [_vis_group(), _vis_group(layer="BOTTOM", spec="3-Y16", bar_count=3)],
        [_det_group(), _det_group(physical_layer="BOTTOM", specification="3Y16", count=3, diameter=16)],
    )
    b = _resolve(
        [_vis_group(layer="BOTTOM", spec="3-Y16", bar_count=3), _vis_group()],
        [_det_group(physical_layer="BOTTOM", specification="3Y16", count=3, diameter=16), _det_group()],
    )
    keys = lambda r: sorted((g["layer"]["resolved_value"], g["bar_count"]["resolved_value"]) for g in r["groups"])
    assert keys(a) == keys(b)


def test_v_rename_invariance() -> None:
    assert rename_invariance().get("ok") is True


def test_w_no_beam_id_source_guard() -> None:
    g = source_guard(_pkg())
    assert g.get("ok") is True, g.get("hits")
    assert g.get("beam_id_special_cases") is False


def test_x_no_production_write() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    assert LIVE_CLAUDE_CALL is False
    leak = runtime_leakage_scan(_pkg())
    assert leak.get("ok") is True, leak.get("hits")
    fw = firewall_check(_v10())
    assert fw.get("ok") is True, fw.get("offenders")


def test_y_prior_fingerprint_immutability() -> None:
    paths = fingerprint_paths(_v10(), {})
    before = capture_fingerprints(paths)
    after = capture_fingerprints(paths)
    cmp = compare_fingerprints(before, after)
    assert cmp.get("unchanged") is True
    intact = prior_artefacts_intact(_v10())
    assert intact.get("ok") is True, intact
    c5 = prior_phase_unit_ok(_v10(), "PhaseP2610C5_stratified_vision_semantic_benchmark", 21)
    assert c5.get("ok") is True, c5


def test_z_duplicate_discovery_stability() -> None:
    rec = {
        "beam_id": "T77",
        "source_phase": "P2.6.10-C.5",
        "usable": True,
        "parsed": {"usable": True, "groups": [_vis_group()], "target_identified": True, "target_beam_id": "T77", "association_confidence": 0.9},
        "detected_groups": [_det_group()],
    }
    dup = dict(rec)
    dup["source_phase"] = "P2.6.10-C.3"
    once = dedupe_observations([rec])
    twice = dedupe_observations([rec, dup, rec])
    assert len(once) == 1
    assert len(twice) == 1
    assert twice[0]["source_phase"] == "P2.6.10-C.5"
    vis = extract_vision_payload(rec["parsed"])
    det = extract_deterministic_groups(rec["detected_groups"])
    r1 = resolve_beam(beam_id="T77", vision=vis, deterministic=det, source_provenance={})
    r2 = resolve_beam(beam_id="T77", vision=vis, deterministic=det, source_provenance={"dup": True})
    assert r1["groups"][0]["diameter"]["resolved_value"] == r2["groups"][0]["diameter"]["resolved_value"]


def test_authority_matrix() -> None:
    for f in VISION_PREFERRED_FIELDS:
        assert is_vision_preferred(f), f
    for f in DETERMINISTIC_AUTHORITY_FIELDS:
        assert not is_vision_preferred(f), f
    assert VISION_MIN_CONFIDENCE == 0.70


def test_possible_duplicate_flag_not_merge() -> None:
    groups = [
        extract_vision_payload({"usable": True, "groups": [_vis_group(), _vis_group()]})["groups"][0],
        extract_vision_payload({"usable": True, "groups": [_vis_group(), _vis_group()]})["groups"][1],
    ]
    flags = flag_possible_duplicates(
        extract_vision_payload({"usable": True, "groups": [_vis_group(physical_group_id="A"), _vis_group(physical_group_id="B")]})["groups"]
    )
    assert flags
    assert flags[0]["code"] == "POSSIBLE_DUPLICATE_GROUP"
    out = _resolve([_vis_group(physical_group_id="A"), _vis_group(physical_group_id="B")], [])
    assert len(out["groups"]) == 2


def test_no_longest_main_override() -> None:
    out = _resolve(
        [
            _vis_group(role_hypothesis="EXTRA", relative_length_evidence="LONGER"),
            _vis_group(layer="BOTTOM", role_hypothesis="MAIN", spec="3-Y16", bar_count=3, relative_length_evidence="SHORTER"),
        ],
        [],
    )
    extra = [g for g in out["groups"] if g["role"]["resolved_value"] == "EXTRA"]
    assert extra
    assert extra[0]["longer_bar_likely_main_hook"] == "ARCHITECTURE_HOOK_ONLY"


def test_anti_bundle() -> None:
    out = run_anti_hardcoding(package_dir=_pkg())
    assert out.get("ok") is True, out


def test_skip_disabled_vision_observation() -> None:
    assert is_live_vision_observation({"called": False}, {"usable": False, "groups": []}) is False
    assert is_live_vision_observation({"called": True}, {"usable": True, "groups": [{"layer": "TOP"}]}) is True


def test_parse_helpers() -> None:
    assert parse_diameter("5-Y20") == 20
    assert parse_bar_count("5-Y20") == 5
    assert parse_bar_count("4L-Y8@100C/C") is None


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("a_valid_vision_accepted", test_a_valid_vision_accepted),
        ("b_low_confidence_rejected", test_b_low_confidence_rejected),
        ("c_invalid_bar_count", test_c_invalid_bar_count),
        ("d_invalid_diameter", test_d_invalid_diameter),
        ("e_spec_count_inconsistent", test_e_spec_count_inconsistent),
        ("f_spec_diameter_inconsistent", test_f_spec_diameter_inconsistent),
        ("g_vision_layer_preferred", test_g_vision_layer_preferred),
        ("h_vision_count_preferred", test_h_vision_count_preferred),
        ("i_vision_diameter_overrides_det", test_i_vision_diameter_overrides_det),
        ("j_vision_spec_preferred", test_j_vision_spec_preferred),
        ("k_vision_role_overrides_det", test_k_vision_role_overrides_det),
        ("l_role_fallback_when_invalid", test_l_role_fallback_when_invalid),
        ("m_diameter_fallback_when_invalid", test_m_diameter_fallback_when_invalid),
        ("n_same_spec_remain_distinct", test_n_same_spec_remain_distinct),
        ("o_vision_only_preserved", test_o_vision_only_preserved),
        ("p_deterministic_only_preserved", test_p_deterministic_only_preserved),
        ("q_stirrup_id_split_from_engineering", test_q_stirrup_id_split_from_engineering),
        ("r_spacer_deterministic", test_r_spacer_deterministic),
        ("s_cut_length_deterministic", test_s_cut_length_deterministic),
        ("t_group_ordering_invariance", test_t_group_ordering_invariance),
        ("u_input_ordering_invariance", test_u_input_ordering_invariance),
        ("v_rename_invariance", test_v_rename_invariance),
        ("w_no_beam_id_source_guard", test_w_no_beam_id_source_guard),
        ("x_no_production_write", test_x_no_production_write),
        ("y_prior_fingerprint_immutability", test_y_prior_fingerprint_immutability),
        ("z_duplicate_discovery_stability", test_z_duplicate_discovery_stability),
        ("authority_matrix", test_authority_matrix),
        ("possible_duplicate_flag_not_merge", test_possible_duplicate_flag_not_merge),
        ("no_longest_main_override", test_no_longest_main_override),
        ("anti_bundle", test_anti_bundle),
        ("parse_helpers", test_parse_helpers),
        ("skip_disabled_vision_observation", test_skip_disabled_vision_observation),
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
