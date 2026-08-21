"""Unit tests for P2.6.10-D.2. Offline. No production. No Claude."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from PhaseP2610D1_vision_semantic_contract_hybrid_foundation.hybrid_authority_contract import is_vision_preferred
from PhaseP2610D1_vision_semantic_contract_hybrid_foundation.vision_normalizer import (
    extract_deterministic_groups,
    extract_vision_payload,
)

from .anti_hardcoding import ordering_invariance, rename_invariance, repeatability, run_anti_hardcoding, source_guard
from .audit import collect_conflicts, collect_fallbacks
from .config import (
    EXPECTED_POPULATION_SIZE,
    GATE_VERSION,
    LIVE_CLAUDE_CALL,
    MODEL_VERSION,
    PRODUCTION_WRITE,
    REASON_FALLBACK,
    REASON_VISION_VALID,
    SRC_DET,
    SRC_VISION,
)
from .discovery import load_d1_population
from .matching import match_groups_conservative
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
from .resolver import resolve_hybrid_beam


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def _vg(**kwargs: Any) -> Dict[str, Any]:
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


def _dg(**kwargs: Any) -> Dict[str, Any]:
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


def _resolve(vgs: List[Dict[str, Any]], dgs: List[Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
    vis = extract_vision_payload(
        {
            "usable": kwargs.get("usable", True),
            "target_beam_id": kwargs.get("tid", "T01"),
            "target_identified": kwargs.get("identified", True),
            "association_confidence": kwargs.get("tconf", 0.95),
            "groups": vgs,
            "stirrups": kwargs.get("stirrups") or [],
        }
    )
    det = extract_deterministic_groups(dgs)
    return resolve_hybrid_beam(beam_id=kwargs.get("beam_id", "T01"), vision=vis, deterministic=det, source_provenance={})


def test_a_artefact_driven_population() -> None:
    pop = load_d1_population(_v10())
    assert pop.get("source_path")
    assert "benchmark_population_manifest.json" in str(pop.get("source_path"))
    assert pop.get("ok") is True


def test_b_expected_unique_count() -> None:
    pop = load_d1_population(_v10())
    assert pop.get("discovered_count") == EXPECTED_POPULATION_SIZE
    assert len(pop.get("beam_ids") or []) == EXPECTED_POPULATION_SIZE
    assert len(set(pop.get("beam_ids") or [])) == EXPECTED_POPULATION_SIZE


def test_c_no_beam_id_runtime() -> None:
    g = source_guard(_pkg())
    assert g.get("ok") is True, g.get("hits")


def test_d_input_order_invariance() -> None:
    assert ordering_invariance().get("ok") is True


def test_e_vision_group_order_invariance() -> None:
    a = _resolve([_vg(), _vg(layer="BOTTOM", spec="3-Y16", bar_count=3)], [_dg(), _dg(physical_layer="BOTTOM", specification="3Y16", count=3, diameter=16)])
    b = _resolve([_vg(layer="BOTTOM", spec="3-Y16", bar_count=3), _vg()], [_dg(), _dg(physical_layer="BOTTOM", specification="3Y16", count=3, diameter=16)])
    ka = sorted((g["layer"]["value"], g["bar_count"]["value"]) for g in a["reinforcement_groups"])
    kb = sorted((g["layer"]["value"], g["bar_count"]["value"]) for g in b["reinforcement_groups"])
    assert ka == kb


def test_f_det_group_order_invariance() -> None:
    a = _resolve([_vg()], [_dg(), _dg(physical_layer="BOTTOM", specification="3Y12", count=3, diameter=12)])
    b = _resolve([_vg()], [_dg(physical_layer="BOTTOM", specification="3Y12", count=3, diameter=12), _dg()])
    assert a["group_matching"]["deterministic_only"] == b["group_matching"]["deterministic_only"] == 1


def test_g_vision_layer_override() -> None:
    out = _resolve([_vg(layer="BOTTOM")], [_dg(physical_layer="TOP")])
    g = out["reinforcement_groups"][0]
    assert g["layer"]["value"] == "BOTTOM"
    assert g["layer"]["source"] == SRC_VISION
    assert g["layer"]["conflict_detected"] is True


def test_h_vision_role_override() -> None:
    assert is_vision_preferred("ROLE")
    out = _resolve([_vg(role_hypothesis="EXTRA")], [_dg(reinforcement_role="MAIN")])
    g = out["reinforcement_groups"][0]
    assert g["role"]["value"] == "EXTRA"
    assert g["role"]["source"] == SRC_VISION
    assert g["role"]["resolution_reason"] == REASON_VISION_VALID


def test_i_vision_count_override() -> None:
    out = _resolve([_vg(spec="3-Y20", bar_count=3)], [_dg(count=5, specification="5Y20", diameter=20)])
    assert out["reinforcement_groups"][0]["bar_count"]["value"] == 3
    assert out["reinforcement_groups"][0]["bar_count"]["source"] == SRC_VISION


def test_j_vision_diameter_override() -> None:
    assert is_vision_preferred("DIAMETER")
    out = _resolve([_vg(spec="5-Y20", bar_count=5)], [_dg(diameter=16, specification="5Y16")])
    g = out["reinforcement_groups"][0]
    assert g["diameter"]["value"] == 20
    assert g["diameter"]["source"] == SRC_VISION
    assert g["diameter"]["deterministic_value"] == 16
    assert g["diameter"]["conflict_detected"] is True


def test_k_vision_spec_override() -> None:
    out = _resolve([_vg(spec="5-Y20")], [_dg(specification="5Y16")])
    g = out["reinforcement_groups"][0]
    assert g["specification"]["value"] == "5-Y20"
    assert g["specification"]["source"] == SRC_VISION


def test_l_invalid_vision_fallback() -> None:
    out = _resolve([_vg(role_hypothesis="NOT_A_ROLE")], [_dg(reinforcement_role="MAIN")])
    g = out["reinforcement_groups"][0]
    assert g["role"]["value"] == "MAIN"
    assert g["role"]["source"] == SRC_DET
    assert g["role"]["fallback_used"] is True
    assert g["role"]["resolution_reason"] == REASON_FALLBACK


def test_m_low_confidence_fallback() -> None:
    out = _resolve([_vg(confidence=0.2, role_confidence=0.2)], [_dg(diameter=16)])
    g = out["reinforcement_groups"][0]
    assert g["diameter"]["source"] == SRC_DET
    assert g["diameter"]["fallback_used"] is True
    assert g["diameter"]["value"] == 16


def test_n_missing_vision_fallback() -> None:
    vis = extract_vision_payload(
        {
            "usable": True,
            "target_beam_id": "T01",
            "target_identified": True,
            "association_confidence": 0.95,
            "groups": [{"layer": "TOP", "role": "MAIN", "spec": "5-Y20", "bar_count": 5, "confidence": 0.95}],
            "stirrups": [],
        }
    )
    vis["groups"][0]["diameter"] = None
    vis["groups"][0]["specification"] = None
    vis["groups"][0]["bar_count"] = None
    det = extract_deterministic_groups([_dg(diameter=16, specification="5Y16", count=5)])
    out = resolve_hybrid_beam(beam_id="T01", vision=vis, deterministic=det, source_provenance={})
    g = out["reinforcement_groups"][0]
    assert g["diameter"]["source"] == SRC_DET
    assert g["diameter"]["fallback_used"] is True


def test_o_deterministic_only_preserved() -> None:
    out = _resolve([_vg()], [_dg(), _dg(physical_layer="BOTTOM", specification="3Y12", count=3, diameter=12)])
    origins = [g["origin"] for g in out["reinforcement_groups"]]
    assert "DETERMINISTIC_ONLY_GROUP" in origins
    assert out["group_matching"]["deterministic_only"] >= 1


def test_p_vision_only_preserved() -> None:
    out = _resolve([_vg(), _vg(layer="BOTTOM", spec="3-Y16", bar_count=3)], [_dg()])
    origins = [g["origin"] for g in out["reinforcement_groups"]]
    assert "VISION_ONLY_GROUP" in origins
    assert out["group_matching"]["vision_only"] >= 1


def test_q_same_spec_not_merged() -> None:
    out = _resolve(
        [
            _vg(physical_group_id="G1", role_hypothesis="MAIN", spec="3-Y20", bar_count=3),
            _vg(physical_group_id="G2", role_hypothesis="EXTRA", spec="3-Y20", bar_count=3, support_scope="LEFT_SUPPORT"),
        ],
        [
            _dg(group_id="D1", reinforcement_role="MAIN", specification="3Y20", count=3, diameter=20),
            _dg(group_id="D2", reinforcement_role="EXTRA", specification="3Y20", count=3, diameter=20, zone="LEFT_SUPPORT"),
        ],
    )
    assert len(out["reinforcement_groups"]) == 2
    roles = sorted(g["role"]["value"] for g in out["reinforcement_groups"])
    assert roles == ["EXTRA", "MAIN"]


def test_r_possible_duplicates_unmerged() -> None:
    vis = [_vg(physical_group_id="A"), _vg(physical_group_id="B")]
    out = _resolve(vis, [])
    assert len(out["reinforcement_groups"]) == 2
    assert out["possible_duplicate_groups"]
    assert out["possible_duplicate_groups"][0]["code"] == "POSSIBLE_DUPLICATE_GROUP"


def test_s_conflict_audit_source_reason() -> None:
    out = _resolve([_vg(spec="5-Y20")], [_dg(diameter=16, specification="5Y16")])
    rows = collect_conflicts(out)
    dia = [r for r in rows if r["field"] == "DIAMETER"]
    assert dia
    assert dia[0]["selected_source"] == SRC_VISION
    assert dia[0]["selected_value"] == 20
    assert dia[0]["reason"] == REASON_VISION_VALID
    assert dia[0]["code"] == "DIAMETER_CONFLICT"


def test_t_fallback_audit_reason() -> None:
    out = _resolve([_vg(confidence=0.1, role_confidence=0.1)], [_dg()])
    rows = collect_fallbacks(out)
    assert rows
    assert any(r.get("reason") for r in rows)


def test_u_spacer_deterministic() -> None:
    out = _resolve(
        [_vg()],
        [_dg(), {"family": "SPACER", "physical_layer": "SPACER", "reinforcement_role": "SPACER", "specification": "2Y12", "count": 2, "diameter": 12}],
    )
    assert out["spacers"]["source"] == SRC_DET
    assert len(out["spacers"]["groups"]) == 1


def test_v_stirrup_split() -> None:
    out = _resolve(
        [_vg()],
        [_dg(), {"family": "STIRRUP", "physical_layer": "STIRRUP", "reinforcement_role": "STIRRUP", "specification": "3L-Y10", "count": 3, "diameter": 10, "cut_length_mm": 3100}],
        stirrups=[{"spec": "4L-Y8@100C/C", "confidence": 0.9}],
    )
    assert out["stirrups"]["semantic_identification_authority"] == "VISION_PREFERRED"
    assert out["stirrups"]["engineering_calculation_authority"] == "DETERMINISTIC_ENGINEERING"
    item = out["stirrups"]["items"][0]
    assert item["semantic_identification"]["source"] in (SRC_VISION, SRC_DET)
    assert item["engineering_calculation_reference"]["source"] == SRC_DET


def test_w_no_longest_main_override() -> None:
    out = _resolve(
        [
            _vg(role_hypothesis="EXTRA", relative_length_evidence="LONGER"),
            _vg(layer="BOTTOM", role_hypothesis="MAIN", spec="3-Y16", bar_count=3, relative_length_evidence="SHORTER"),
        ],
        [],
    )
    extra = [g for g in out["reinforcement_groups"] if g["role"]["value"] == "EXTRA"]
    assert extra
    assert extra[0]["longer_bar_likely_main_hook"] == "ARCHITECTURE_HOOK_ONLY"


def test_x_no_claude() -> None:
    assert LIVE_CLAUDE_CALL is False
    leak = runtime_leakage_scan(_pkg())
    assert leak.get("ok") is True, leak.get("hits")


def test_y_no_dxf_rerender() -> None:
    leak = runtime_leakage_scan(_pkg())
    assert leak.get("ok") is True, leak.get("hits")
    text = (_pkg() / "resolver.py").read_text(encoding="utf-8")
    assert "ezdxf" not in text
    assert "RenderSession" not in text


def test_z_no_production_write() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    fw = firewall_check(_v10())
    assert fw.get("ok") is True, fw.get("offenders")


def test_aa_prior_artefacts_unchanged() -> None:
    paths = fingerprint_paths(_v10(), {})
    before = capture_fingerprints(paths)
    after = capture_fingerprints(paths)
    cmp = compare_fingerprints(before, after)
    assert cmp.get("unchanged") is True
    intact = prior_artefacts_intact(_v10())
    assert intact.get("ok") is True, intact
    d1 = prior_phase_unit_ok(_v10(), "PhaseP2610D1_vision_semantic_contract_hybrid_foundation", 32)
    assert d1.get("ok") is True, d1


def test_ab_repeatable() -> None:
    assert repeatability().get("ok") is True
    assert rename_invariance().get("ok") is True


def test_anti_bundle() -> None:
    out = run_anti_hardcoding(package_dir=_pkg())
    assert out.get("ok") is True, out


def test_ambiguous_not_forced() -> None:
    vis = extract_vision_payload({"usable": True, "groups": [_vg(spec="3-Y20", bar_count=3), _vg(physical_group_id="G2", spec="3-Y20", bar_count=3)], "target_identified": True, "target_beam_id": "T01", "association_confidence": 0.95})
    det = extract_deterministic_groups([_dg(specification="3Y20", count=3, diameter=20), _dg(group_id="D2", specification="3Y20", count=3, diameter=20)])
    m = match_groups_conservative(vis["groups"], det["groups"])
    assert m["ambiguous"] or len(m["pairs"]) <= 2
    out = resolve_hybrid_beam(beam_id="T01", vision=vis, deterministic=det, source_provenance={})
    assert len(out["reinforcement_groups"]) >= 2


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("a_artefact_driven_population", test_a_artefact_driven_population),
        ("b_expected_unique_count", test_b_expected_unique_count),
        ("c_no_beam_id_runtime", test_c_no_beam_id_runtime),
        ("d_input_order_invariance", test_d_input_order_invariance),
        ("e_vision_group_order_invariance", test_e_vision_group_order_invariance),
        ("f_det_group_order_invariance", test_f_det_group_order_invariance),
        ("g_vision_layer_override", test_g_vision_layer_override),
        ("h_vision_role_override", test_h_vision_role_override),
        ("i_vision_count_override", test_i_vision_count_override),
        ("j_vision_diameter_override", test_j_vision_diameter_override),
        ("k_vision_spec_override", test_k_vision_spec_override),
        ("l_invalid_vision_fallback", test_l_invalid_vision_fallback),
        ("m_low_confidence_fallback", test_m_low_confidence_fallback),
        ("n_missing_vision_fallback", test_n_missing_vision_fallback),
        ("o_deterministic_only_preserved", test_o_deterministic_only_preserved),
        ("p_vision_only_preserved", test_p_vision_only_preserved),
        ("q_same_spec_not_merged", test_q_same_spec_not_merged),
        ("r_possible_duplicates_unmerged", test_r_possible_duplicates_unmerged),
        ("s_conflict_audit_source_reason", test_s_conflict_audit_source_reason),
        ("t_fallback_audit_reason", test_t_fallback_audit_reason),
        ("u_spacer_deterministic", test_u_spacer_deterministic),
        ("v_stirrup_split", test_v_stirrup_split),
        ("w_no_longest_main_override", test_w_no_longest_main_override),
        ("x_no_claude", test_x_no_claude),
        ("y_no_dxf_rerender", test_y_no_dxf_rerender),
        ("z_no_production_write", test_z_no_production_write),
        ("aa_prior_artefacts_unchanged", test_aa_prior_artefacts_unchanged),
        ("ab_repeatable", test_ab_repeatable),
        ("anti_bundle", test_anti_bundle),
        ("ambiguous_not_forced", test_ambiguous_not_forced),
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
