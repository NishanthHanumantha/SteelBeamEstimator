"""Unit tests for P2.6.10-D.3. Offline. No production. No Claude. No calculations."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from .anti_hardcoding import (
    _bind,
    _group,
    det_ref_order_invariance,
    group_order_invariance,
    input_order_invariance,
    rename_invariance,
    repeatability,
    run_anti_hardcoding,
    sample_hybrid,
    sample_model,
    source_guard,
)
from .config import (
    EXPECTED_POPULATION_SIZE,
    GATE_VERSION,
    LIVE_CLAUDE_CALL,
    MODEL_VERSION,
    PRODUCTION_WRITE,
    STATUS_AMBIGUOUS,
    STATUS_BOUND,
    STATUS_MISSING_GEOM,
    STATUS_MISSING_RULE,
)
from .engineering_rule_binder import default_rule_catalog
from .hybrid_binding_engine import bind_beam
from .input_loader import load_d2_hybrids, load_d2_population
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from .provenance import semantic_snapshot
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    prior_artefacts_intact,
    prior_phase_unit_ok,
    runtime_leakage_scan,
)


def _v10() -> Path:
    return Path(__file__).resolve().parents[2]


def _pkg() -> Path:
    return Path(__file__).resolve().parent


def test_a_source_guard() -> None:
    g = source_guard(_pkg())
    assert g.get("ok") is True, g.get("hits")


def test_b_rename_invariance() -> None:
    assert rename_invariance().get("ok") is True


def test_c_input_order_invariance() -> None:
    assert input_order_invariance().get("ok") is True


def test_d_group_order_invariance() -> None:
    assert group_order_invariance().get("ok") is True


def test_e_det_ref_order_invariance() -> None:
    assert det_ref_order_invariance().get("ok") is True


def test_f_vision_only_binding() -> None:
    hybrid = sample_hybrid("T01", [_group(gid="VG1", origin="VISION_ONLY_GROUP")])
    out = _bind("T01", hybrid)
    g = out["groups"][0]
    assert g["origin"] == "VISION_ONLY_GROUP"
    bind = g["engineering_binding"]
    assert bind["beam_geometry_reference"] is not None
    assert bind["cut_length_rule_reference"] is not None
    assert bind["binding_status"] in (STATUS_BOUND, "PARTIALLY_BOUND")


def test_g_deterministic_only_preserved() -> None:
    hybrid = sample_hybrid(
        "T01",
        [
            _group(gid="G1", origin="MATCHED", cut=8000),
            _group(gid="D2", origin="DETERMINISTIC_ONLY_GROUP", layer="BOTTOM", spec="3Y12", count=3, diameter=12),
        ],
    )
    out = _bind("T01", hybrid)
    origins = [g["origin"] for g in out["groups"]]
    assert "DETERMINISTIC_ONLY_GROUP" in origins
    det = [g for g in out["groups"] if g["origin"] == "DETERMINISTIC_ONLY_GROUP"][0]
    assert det["engineering_binding"]["binding_status"] in (STATUS_BOUND, "PARTIALLY_BOUND")


def test_h_ambiguous_not_force_bound() -> None:
    g = _group(gid="VG2", origin="VISION_ONLY_GROUP", scope="BOTH_SUPPORTS")
    hybrid = sample_hybrid("T01", [g])
    hybrid["group_matching"]["ambiguous"] = 1
    hybrid["group_matching"]["ambiguous_records"] = [
        {"code": "AMBIGUOUS_GROUP_MATCH", "vision_id": "VG2", "reason": "TIED_TOP_SCORE"}
    ]
    out = _bind("T01", hybrid)
    row = out["groups"][0]
    assert row["ambiguous"] is True
    assert row["engineering_binding"]["binding_status"] == STATUS_AMBIGUOUS


def test_i_possible_duplicates_not_merged() -> None:
    g1 = _group(gid="A", origin="VISION_ONLY_GROUP")
    g2 = _group(gid="B", origin="VISION_ONLY_GROUP")
    hybrid = sample_hybrid("T01", [g1, g2])
    hybrid["possible_duplicate_groups"] = [{"code": "POSSIBLE_DUPLICATE_GROUP", "group_ids": ["A", "B"]}]
    out = _bind("T01", hybrid)
    assert len(out["groups"]) == 2
    assert all(g.get("possible_duplicate") for g in out["groups"])
    ids = {g["group_id"] for g in out["groups"]}
    assert ids == {"A", "B"}


def test_j_diameter_authority() -> None:
    g = _group(gid="G1", origin="MATCHED", diameter=20, spec="5-Y20", cut=1000)
    out = _bind("T01", sample_hybrid("T01", [g]))
    sem = out["groups"][0]["semantic"]
    assert sem["diameter"] == 20
    assert sem["field_records"]["diameter"]["source"] == "VISION"
    assert sem["field_records"]["diameter"]["value"] == 20


def test_k_role_authority() -> None:
    g = _group(gid="G1", origin="VISION_ONLY_GROUP", role="EXTRA")
    out = _bind("T01", sample_hybrid("T01", [g]))
    assert out["groups"][0]["semantic"]["role"] == "EXTRA"
    assert out["groups"][0]["semantic"]["field_records"]["role"]["source"] == "VISION"


def test_l_spacer_authority() -> None:
    out = _bind("T01", sample_hybrid("T01"))
    assert out["spacers"]["source"] == "DETERMINISTIC"
    assert out["spacers"]["binding_status"] == STATUS_BOUND
    assert out["spacers"]["vision_matched"] is False


def test_m_stirrup_authority_split() -> None:
    out = _bind("T01", sample_hybrid("T01"))
    assert out["stirrups"]
    s = out["stirrups"][0]
    assert s["semantic_identification_authority"] == "VISION_PREFERRED"
    assert s["engineering_calculation_authority"] == "DETERMINISTIC_ENGINEERING"
    assert s["engineering_binding"]["quantities_calculated"] is False
    assert s["engineering_binding"]["si_replaced"] is False


def test_n_no_longest_bar_main_override() -> None:
    extra = _group(gid="G1", origin="VISION_ONLY_GROUP", role="EXTRA")
    extra["relative_span_length"] = "LONGER"
    main = _group(gid="G2", origin="VISION_ONLY_GROUP", role="MAIN", layer="BOTTOM", spec="3-Y16", count=3, diameter=16)
    main["relative_span_length"] = "SHORTER"
    out = _bind("T01", sample_hybrid("T01", [extra, main]))
    roles = {g["group_id"]: g["semantic"]["role"] for g in out["groups"]}
    assert roles["G1"] == "EXTRA"
    assert roles["G2"] == "MAIN"
    assert all(g["semantic"]["longer_bar_likely_main_hook"] == "ARCHITECTURE_HOOK_ONLY" for g in out["groups"])
    assert out["compatibility"]["longest_bar_main_override"] is False


def test_o_fail_closed_missing_geometry() -> None:
    hybrid = sample_hybrid("T01", [_group(gid="G1", origin="MATCHED")])
    out = bind_beam(hybrid=hybrid, catalog={}, rule_catalog=default_rule_catalog())
    assert out["groups"][0]["engineering_binding"]["binding_status"] == STATUS_MISSING_GEOM
    assert out["groups"][0]["engineering_binding"]["beam_geometry_reference"] is None


def test_p_fail_closed_missing_rule() -> None:
    hybrid = sample_hybrid("T01", [_group(gid="G1", origin="MATCHED", cut=1000)])
    out = bind_beam(hybrid=hybrid, catalog={"T01": sample_model()}, rule_catalog={})
    assert out["groups"][0]["engineering_binding"]["binding_status"] == STATUS_MISSING_RULE
    assert out["groups"][0]["engineering_binding"]["cut_length_rule_reference"] is None


def test_q_repeatability() -> None:
    assert repeatability().get("ok") is True


def test_artefact_population() -> None:
    pop = load_d2_population(_v10())
    assert pop.get("ok") is True
    assert pop.get("discovered_count") == EXPECTED_POPULATION_SIZE
    assert len(set(pop.get("beam_ids") or [])) == EXPECTED_POPULATION_SIZE
    hy = load_d2_hybrids(_v10())
    assert hy.get("ok") is True
    for bid in pop.get("beam_ids") or []:
        assert bid in hy.get("by_id")


def test_no_claude() -> None:
    assert LIVE_CLAUDE_CALL is False
    leak = runtime_leakage_scan(_pkg())
    assert leak.get("ok") is True, leak.get("hits")


def test_no_production_write() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    fw = firewall_check(_v10())
    assert fw.get("ok") is True, fw.get("offenders")


def test_prior_artefacts() -> None:
    paths = fingerprint_paths(_v10(), {})
    before = capture_fingerprints(paths)
    after = capture_fingerprints(paths)
    cmp = compare_fingerprints(before, after)
    assert cmp.get("unchanged") is True
    intact = prior_artefacts_intact(_v10())
    assert intact.get("ok") is True, intact
    d1 = prior_phase_unit_ok(_v10(), "PhaseP2610D1_vision_semantic_contract_hybrid_foundation", 32)
    d2 = prior_phase_unit_ok(_v10(), "PhaseP2610D2_shadow_hybrid_semantic_resolver", 30)
    assert d1.get("ok") is True, d1
    assert d2.get("ok") is True, d2


def test_no_calculations() -> None:
    out = _bind("T01", sample_hybrid("T01"))
    calc = out["groups"][0]["engineering_binding"]["calculated"]
    assert calc["cut_length"] is False
    assert calc["development_length"] is False
    assert calc["steel_weight"] is False
    assert out["compatibility"]["calculations_performed"]["bbs"] is False


def test_anti_bundle() -> None:
    out = run_anti_hardcoding(package_dir=_pkg())
    assert out.get("ok") is True, out


def test_semantic_snapshot_stable() -> None:
    g = _group(gid="G1", origin="MATCHED", diameter=20, role="MAIN")
    hybrid = sample_hybrid("T01", [g])
    snap = semantic_snapshot(hybrid=hybrid, group=g)
    out = _bind("T01", hybrid)
    bound_sem = out["groups"][0]["semantic"]
    assert bound_sem["diameter"] == snap["diameter"] == 20
    assert bound_sem["role"] == snap["role"] == "MAIN"


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("a_source_guard", test_a_source_guard),
        ("b_rename_invariance", test_b_rename_invariance),
        ("c_input_order_invariance", test_c_input_order_invariance),
        ("d_group_order_invariance", test_d_group_order_invariance),
        ("e_det_ref_order_invariance", test_e_det_ref_order_invariance),
        ("f_vision_only_binding", test_f_vision_only_binding),
        ("g_deterministic_only_preserved", test_g_deterministic_only_preserved),
        ("h_ambiguous_not_force_bound", test_h_ambiguous_not_force_bound),
        ("i_possible_duplicates_not_merged", test_i_possible_duplicates_not_merged),
        ("j_diameter_authority", test_j_diameter_authority),
        ("k_role_authority", test_k_role_authority),
        ("l_spacer_authority", test_l_spacer_authority),
        ("m_stirrup_authority_split", test_m_stirrup_authority_split),
        ("n_no_longest_bar_main_override", test_n_no_longest_bar_main_override),
        ("o_fail_closed_missing_geometry", test_o_fail_closed_missing_geometry),
        ("p_fail_closed_missing_rule", test_p_fail_closed_missing_rule),
        ("q_repeatability", test_q_repeatability),
        ("artefact_population", test_artefact_population),
        ("no_claude", test_no_claude),
        ("no_production_write", test_no_production_write),
        ("prior_artefacts", test_prior_artefacts),
        ("no_calculations", test_no_calculations),
        ("anti_bundle", test_anti_bundle),
        ("semantic_snapshot_stable", test_semantic_snapshot_stable),
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
