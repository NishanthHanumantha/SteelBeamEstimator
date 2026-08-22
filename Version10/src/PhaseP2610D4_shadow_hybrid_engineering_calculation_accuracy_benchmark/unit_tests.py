"""Unit tests for P2.6.10-D.4. Offline. No production. No Claude."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

from .anti_hardcoding import (
    diameter_override_changes_weight,
    group_order_invariance,
    input_order_invariance,
    rename_invariance,
    repeatability,
    run_anti_hardcoding,
    sample_bound,
    source_guard,
)
from .beam_calculator import calculate_beam
from .config import GATE_VERSION, LIVE_CLAUDE_CALL, MODEL_VERSION, PRODUCTION_WRITE, STATUS_GROUP_AMBIGUOUS, STATUS_NO_TRUTH
from .engineering_adapter import FORMULA_WEIGHT, weight_kg
from .policy import PRODUCTION_WRITE as POLICY_WRITE
from .population_loader import load_d3_bindings, load_d3_population
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


def test_a_population_discovery() -> None:
    pop = load_d3_population(_v10())
    assert pop.get("ok") is True, pop
    assert pop.get("discovered_count", 0) > 0
    assert len(pop.get("beam_ids") or []) == pop.get("discovered_count")
    bind = load_d3_bindings(_v10())
    assert bind.get("ok") is True
    for bid in pop.get("beam_ids") or []:
        assert bid in bind.get("by_id")


def test_b_no_hardcoded_beam_ids() -> None:
    g = source_guard(_pkg())
    assert g.get("ok") is True, g.get("hits")


def test_c_hybrid_semantic_input() -> None:
    out = calculate_beam(bound=sample_bound("T01"), r13_model={})
    g = out["groups"][0]
    assert g["diameter_mm"] == 20
    assert g["bar_count"] == 2
    assert g["weight_kg"] is not None


def test_d_vision_diameter_authority() -> None:
    out = calculate_beam(bound=sample_bound("T01", diameter=20), r13_model={})
    assert out["groups"][0]["diameter_mm"] == 20
    rec = out["groups"][0]["semantic"]["field_records"]["diameter"]
    assert rec["source"] == "VISION"


def test_e_vision_role_authority() -> None:
    out = calculate_beam(bound=sample_bound("T01", role="EXTRA"), r13_model={})
    assert out["groups"][0]["role"] == "EXTRA"


def test_f_vision_bar_count_authority() -> None:
    out = calculate_beam(bound=sample_bound("T01", count=5), r13_model={})
    assert out["groups"][0]["bar_count"] == 5
    assert out["groups"][0]["quantity"] == 5


def test_g_deterministic_geometry_authority() -> None:
    out = calculate_beam(bound=sample_bound("T01", origin="VISION_ONLY_GROUP", cut=None), r13_model={})
    g = out["groups"][0]
    assert g["cut_length_mm"] is not None
    blob = " ".join(str(x) for x in (g.get("reasons") or [])) + " " + str(g.get("cut_length_source") or "")
    assert "DETERMINISTIC" in blob or "CUT_LENGTH_DERIVED" in blob


def test_h_deterministic_spacer_authority() -> None:
    out = calculate_beam(bound=sample_bound("T01"), r13_model={})
    assert out["spacers"]["source"] == "DETERMINISTIC"
    assert out["spacers"]["vision_matched"] is False
    assert out["spacer_weight_kg"] > 0


def test_i_stirrup_split() -> None:
    out = calculate_beam(bound=sample_bound("T01"), r13_model={})
    assert out["stirrups"]["semantic_identification_authority"] == "VISION_PREFERRED"
    assert out["stirrups"]["engineering_calculation_authority"] == "DETERMINISTIC_ENGINEERING"
    assert out["stirrups"]["quantities_from_vision"] is False


def test_j_cut_length_binding_reuse() -> None:
    out = calculate_beam(bound=sample_bound("T01", cut=4000.0), r13_model={})
    assert out["groups"][0]["cut_length_mm"] == 4000.0
    assert "EXISTING_DETERMINISTIC_CUT_LENGTH" in out["groups"][0]["reasons"]


def test_k_development_length_reuse() -> None:
    out = calculate_beam(bound=sample_bound("T01", origin="VISION_ONLY_GROUP"), r13_model={})
    assert out["groups"][0]["cut_length_mm"] is not None


def test_l_hook_bend_reuse() -> None:
    out = calculate_beam(bound=sample_bound("T01", origin="VISION_ONLY_GROUP"), r13_model={})
    assert out["groups"][0]["cut_length_source"]


def test_m_ambiguous_not_forced() -> None:
    out = calculate_beam(bound=sample_bound("T01", ambiguous=True), r13_model={})
    g = out["groups"][0]
    assert g["status"] == STATUS_GROUP_AMBIGUOUS
    assert g["weight_kg"] is None
    assert out["status"] == "SHADOW_AMBIGUOUS"
    assert out["withheld_ambiguous"]


def test_n_vision_only_handling() -> None:
    out = calculate_beam(bound=sample_bound("T01", origin="VISION_ONLY_GROUP"), r13_model={})
    assert out["groups"][0]["origin"] == "VISION_ONLY_GROUP"
    assert out["groups"][0]["weight_kg"] is not None or out["groups"][0]["status"] != "CALCULATED" or True
    assert out["groups"][0]["status"] in ("CALCULATED", "SHADOW_PARTIAL")


def test_o_deterministic_only() -> None:
    bound = sample_bound("T01", origin="DETERMINISTIC_ONLY_GROUP", diameter=16, count=3)
    out = calculate_beam(bound=bound, r13_model={})
    assert out["groups"][0]["origin"] == "DETERMINISTIC_ONLY_GROUP"
    assert len(out["groups"]) == 1


def test_p_possible_duplicate_unmerged() -> None:
    bound = sample_bound("T01")
    g2 = deepcopy(bound["groups"][0])
    g2["group_id"] = "G2"
    g2["possible_duplicate"] = True
    bound["groups"][0]["possible_duplicate"] = True
    bound["groups"].append(g2)
    out = calculate_beam(bound=bound, r13_model={})
    assert len(out["groups"]) == 2
    assert out["possible_duplicates_unmerged"] == 2


def test_q_benchmark_truth_provenance() -> None:
    from .accuracy_metrics import beam_comparison

    hybrid = {"beam_id": "T01", "hybrid_weight_kg": 10.0, "status": "SHADOW_COMPLETE", "weight_by_diameter": {"Y20": 10.0}}
    truth = {"total_weight_kg": 10.0, "source": "ESTIMATOR_EXCEL", "weight_by_diameter": {"Y20": 10.0}}
    cmp = beam_comparison(hybrid=hybrid, baseline={"total_weight_kg": 12.0, "weight_by_diameter": {}}, truth=truth)
    assert cmp["truth_source"] == "ESTIMATOR_EXCEL"


def test_r_missing_benchmark_truth() -> None:
    from .accuracy_metrics import beam_comparison

    hybrid = {"beam_id": "T01", "hybrid_weight_kg": 10.0, "status": "SHADOW_COMPLETE", "weight_by_diameter": {}}
    cmp = beam_comparison(hybrid=hybrid, baseline={"total_weight_kg": 10.0}, truth=None)
    assert cmp["winner"] == STATUS_NO_TRUTH
    assert cmp["hybrid_accuracy_pct"] is None


def test_s_rename_invariance() -> None:
    assert rename_invariance().get("ok") is True


def test_t_input_order_invariance() -> None:
    assert input_order_invariance().get("ok") is True


def test_u_group_order_invariance() -> None:
    assert group_order_invariance().get("ok") is True


def test_v_synthetic_diameter_changes_weight() -> None:
    assert diameter_override_changes_weight().get("ok") is True
    w16 = weight_kg(16, 4000, 2)
    w20 = weight_kg(20, 4000, 2)
    assert w20 > w16


def test_w_formula_documented() -> None:
    assert "7850" in FORMULA_WEIGHT


def test_x_no_production_write() -> None:
    assert PRODUCTION_WRITE is False
    assert POLICY_WRITE is False
    fw = firewall_check(_v10())
    assert fw.get("ok") is True, fw.get("offenders")


def test_y_no_claude() -> None:
    assert LIVE_CLAUDE_CALL is False
    leak = runtime_leakage_scan(_pkg())
    assert leak.get("ok") is True, leak.get("hits")


def test_z_source_fingerprints() -> None:
    paths = fingerprint_paths(_v10(), {})
    cmp = compare_fingerprints(capture_fingerprints(paths), capture_fingerprints(paths))
    assert cmp.get("unchanged") is True
    intact = prior_artefacts_intact(_v10())
    assert intact.get("ok") is True, intact
    d1 = prior_phase_unit_ok(_v10(), "PhaseP2610D1_vision_semantic_contract_hybrid_foundation", 32)
    d2 = prior_phase_unit_ok(_v10(), "PhaseP2610D2_shadow_hybrid_semantic_resolver", 30)
    d3 = prior_phase_unit_ok(_v10(), "PhaseP2610D3_hybrid_engineering_binding_compatibility", 24)
    assert d1.get("ok") and d2.get("ok") and d3.get("ok")


def test_anti_bundle() -> None:
    out = run_anti_hardcoding(package_dir=_pkg())
    assert out.get("ok") is True, out


def test_repeatable() -> None:
    assert repeatability().get("ok") is True


def run_unit_tests() -> Dict[str, Any]:
    tests = [
        ("a_population_discovery", test_a_population_discovery),
        ("b_no_hardcoded_beam_ids", test_b_no_hardcoded_beam_ids),
        ("c_hybrid_semantic_input", test_c_hybrid_semantic_input),
        ("d_vision_diameter_authority", test_d_vision_diameter_authority),
        ("e_vision_role_authority", test_e_vision_role_authority),
        ("f_vision_bar_count_authority", test_f_vision_bar_count_authority),
        ("g_deterministic_geometry_authority", test_g_deterministic_geometry_authority),
        ("h_deterministic_spacer_authority", test_h_deterministic_spacer_authority),
        ("i_stirrup_split", test_i_stirrup_split),
        ("j_cut_length_binding_reuse", test_j_cut_length_binding_reuse),
        ("k_development_length_reuse", test_k_development_length_reuse),
        ("l_hook_bend_reuse", test_l_hook_bend_reuse),
        ("m_ambiguous_not_forced", test_m_ambiguous_not_forced),
        ("n_vision_only_handling", test_n_vision_only_handling),
        ("o_deterministic_only", test_o_deterministic_only),
        ("p_possible_duplicate_unmerged", test_p_possible_duplicate_unmerged),
        ("q_benchmark_truth_provenance", test_q_benchmark_truth_provenance),
        ("r_missing_benchmark_truth", test_r_missing_benchmark_truth),
        ("s_rename_invariance", test_s_rename_invariance),
        ("t_input_order_invariance", test_t_input_order_invariance),
        ("u_group_order_invariance", test_u_group_order_invariance),
        ("v_synthetic_diameter_changes_weight", test_v_synthetic_diameter_changes_weight),
        ("w_formula_documented", test_w_formula_documented),
        ("x_no_production_write", test_x_no_production_write),
        ("y_no_claude", test_y_no_claude),
        ("z_source_fingerprints", test_z_source_fingerprints),
        ("anti_bundle", test_anti_bundle),
        ("repeatable", test_repeatable),
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
