"""
Focused unit tests for P2.3 controlled production gate.
MODEL_VERSION: 10.5.5
"""
from __future__ import annotations

from typing import Any, Dict, List

from .candidate_gate import select_controlled_candidates
from .config import MODEL_VERSION, PHASE_ID, PRODUCTION_POLICY, REFERENCE_POSITIVE_KEY
from .overlay import apply_overlay
from .regression import validate_no_unexplained_migration


def _e_cand(**overrides: Any) -> Dict[str, Any]:
    base = {
        "beam_id": "B16",
        "leader_id": "LDR::7A1FFD68",
        "stable_key": REFERENCE_POSITIVE_KEY,
        "enhanced_policy": PRODUCTION_POLICY,
        "enhanced_decision": "ACCEPT_CANDIDATE",
        "enhanced_reason": "strong_chain_bar_context_with_endpoint_or_longitudinal_evidence",
        "chain_continuity": True,
        "bar_proximity": True,
        "target_beam_context": True,
        "endpoint_near_envelope": True,
        "longitudinal_overlap": False,
        "neighbour_ambiguity": False,
        "inside_other_beam_envelope": False,
        "policy_results": {
            "A_CURRENT": False,
            "B_CHAIN_EVIDENCE": True,
            "C_CHAIN_ENDPOINT": True,
            "D_CHAIN_GEOMETRIC": False,
            "E_STRONG_COMBINED": True,
        },
        "recovery_potential": "HIGH",
    }
    base.update(overrides)
    return base


def run_unit_tests() -> Dict[str, Any]:
    tests: List[Dict[str, Any]] = []

    def add(tid: str, name: str, ok: bool, detail: Any = None) -> None:
        tests.append({"test_id": tid, "name": name, "pass": bool(ok), "detail": detail})

    # 1. P2.2 E candidate accepted
    sel = select_controlled_candidates(
        p22_production={"candidates": [_e_cand()]},
        p22_decisions={"decisions": []},
        recovery_enabled=True,
    )
    add(
        "UT_01",
        "P2.2 E candidate is accepted",
        sel["accepted_count"] == 1
        and sel["accepted_keys"] == [REFERENCE_POSITIVE_KEY],
        sel["accepted_keys"],
    )

    # 2. Policy D cannot enter production
    d_only = _e_cand(
        enhanced_policy="D_CHAIN_GEOMETRIC",
        enhanced_decision="ACCEPT_CANDIDATE",
        policy_results={
            "A_CURRENT": False,
            "B_CHAIN_EVIDENCE": False,
            "C_CHAIN_ENDPOINT": False,
            "D_CHAIN_GEOMETRIC": True,
            "E_STRONG_COMBINED": False,
        },
        bar_proximity=False,
        endpoint_near_envelope=False,
        longitudinal_overlap=True,
        stable_key="B18::LDR::0A172EB7",
        leader_id="LDR::0A172EB7",
        beam_id="B18",
    )
    sel2 = select_controlled_candidates(
        p22_production={"candidates": [d_only]},
        p22_decisions={"decisions": []},
        recovery_enabled=True,
    )
    add(
        "UT_02",
        "Policy D cannot enter production",
        sel2["accepted_count"] == 0,
        sel2["rejected"][0].get("gate_reason") if sel2["rejected"] else None,
    )

    # 3. B16 candidate accepted
    add(
        "UT_03",
        "B16 candidate is accepted",
        REFERENCE_POSITIVE_KEY in sel["accepted_keys"],
    )

    # 4-8. Fail-closed rejects
    cases = [
        ("UT_04", "neighbour ambiguity rejected", {"neighbour_ambiguity": True}),
        ("UT_05", "inside-other-beam rejected", {"inside_other_beam_envelope": True}),
        ("UT_06", "missing bar proximity rejected", {"bar_proximity": False}),
        ("UT_07", "missing target context rejected", {"target_beam_context": False}),
        ("UT_08", "missing chain continuity rejected", {"chain_continuity": False}),
    ]
    for tid, name, ov in cases:
        s = select_controlled_candidates(
            p22_production={"candidates": [_e_cand(**ov)]},
            p22_decisions={"decisions": []},
            recovery_enabled=True,
        )
        add(tid, name, s["accepted_count"] == 0, (s["rejected"] or [{}])[0].get("gate_reason"))

    # 9. No unexplained migration
    baseline = {
        "by_beam": {
            "B16": {
                "accepted_node_ids": ["ANN-62d4cbc2", "BAR::SYN::B16::1213781"],
                "leader_results": {
                    "LDR::7A1FFD68": {
                        "accepted": False,
                        "rejected_rule": "R2_LEADER_TIP",
                    }
                },
                "accepted_chains": [
                    {
                        "annotation_id": "ANN-62d4cbc2",
                        "leaders": ["LDR::7A1FFD68"],
                        "describes": ["BAR::SYN::B16::1213781"],
                    }
                ],
            }
        }
    }
    graph = {
        "nodes": [
            {
                "id": "LDR::7A1FFD68",
                "type": "Leader",
                "beam_id": "B16",
                "relationships": [
                    {
                        "type": "HAS_ARROW",
                        "direction": "out",
                        "other_id": "ARR::4C3D2D29",
                        "edge_id": "E1",
                    },
                    {
                        "type": "TARGETS",
                        "direction": "out",
                        "other_id": "LTGT::LDR::7A1FFD68",
                        "edge_id": "E2",
                    },
                ],
            },
            {"id": "ARR::4C3D2D29", "type": "LeaderArrow", "beam_id": "B16"},
            {"id": "LTGT::LDR::7A1FFD68", "type": "LeaderTarget", "beam_id": "B16"},
        ],
        "edges": [],
    }
    ov = apply_overlay(
        baseline_ownership=baseline,
        graph=graph,
        accepted_candidates=sel["accepted"],
        mode="CONTROLLED",
    )
    mig_val = validate_no_unexplained_migration(ov["migrations"])
    add("UT_09", "no unexplained ownership migration", mig_val["pass"], mig_val)

    # 10. Downstream propagation has provenance
    add(
        "UT_10",
        "downstream propagation has provenance",
        len(ov["propagation"]) == 1
        and all(
            n.get("evidence_source") in ("P2.2", "T18_existing")
            for n in ov["propagation"][0].get("nodes") or []
        ),
        ov["propagation"][0].get("propagated_graph_children") if ov["propagation"] else None,
    )

    # 11. Deterministic migration
    ov2 = apply_overlay(
        baseline_ownership=baseline,
        graph=graph,
        accepted_candidates=sel["accepted"],
        mode="CONTROLLED",
    )
    add(
        "UT_11",
        "deterministic migration",
        ov["migrations"] == ov2["migrations"]
        and ov["added_entity_ids"] == ov2["added_entity_ids"],
    )

    # 12. Baseline mode reproduces existing ownership
    base_mode = apply_overlay(
        baseline_ownership=baseline,
        graph=graph,
        accepted_candidates=sel["accepted"],
        mode="BASELINE",
    )
    add(
        "UT_12",
        "baseline mode reproduces existing ownership exactly",
        base_mode["migrations"] == []
        and base_mode["ownership"]["by_beam"]["B16"]["accepted_node_ids"]
        == baseline["by_beam"]["B16"]["accepted_node_ids"],
    )

    # 13. Controlled differs only by valid P2.2 candidates
    base_ids = set(baseline["by_beam"]["B16"]["accepted_node_ids"])
    ctrl_ids = set(ov["ownership"]["by_beam"]["B16"]["accepted_node_ids"])
    delta = ctrl_ids - base_ids
    add(
        "UT_13",
        "controlled mode differs only by valid P2.2 candidates",
        "LDR::7A1FFD68" in delta
        and delta.issubset({"LDR::7A1FFD68", "ARR::4C3D2D29", "LTGT::LDR::7A1FFD68"}),
        sorted(delta),
    )

    # 14. No global envelope expansion
    add(
        "UT_14",
        "no global envelope expansion occurs",
        "envelope" not in str(ov["migrations"]).lower()
        or all("envelope" not in (m.get("reason") or "").lower() for m in ov["migrations"]),
        True,
    )

    # Extra: recovery disabled
    off = select_controlled_candidates(
        p22_production={"candidates": [_e_cand()]},
        p22_decisions={"decisions": []},
        recovery_enabled=False,
    )
    add("UT_15", "gate OFF rejects all", off["accepted_count"] == 0)

    failed = [t for t in tests if not t["pass"]]
    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "overall_pass": len(failed) == 0,
        "passed": sum(1 for t in tests if t["pass"]),
        "failed": len(failed),
        "total": len(tests),
        "tests": tests,
        "failed_ids": [t["test_id"] for t in failed],
    }


if __name__ == "__main__":
    import json
    import sys

    r = run_unit_tests()
    print(json.dumps({k: r[k] for k in ("overall_pass", "passed", "failed", "total", "failed_ids")}, indent=2))
    for t in r["tests"]:
        print(("PASS" if t["pass"] else "FAIL"), t["test_id"], t["name"])
    raise SystemExit(0 if r["overall_pass"] else 1)
