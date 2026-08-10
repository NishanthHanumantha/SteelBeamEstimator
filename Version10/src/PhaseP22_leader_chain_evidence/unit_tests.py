"""
Focused unit tests for LeaderChainEvidenceEvaluator.
MODEL_VERSION: 10.5.4

Boolean boundary conditions — no magic distance thresholds.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .config import (
    MODEL_VERSION,
    PHASE_ID,
    PRODUCTION_POLICY,
    EnhancedDecision,
    ProductionGate,
)
from .evaluator import LeaderChainEvidenceEvaluator, LeaderEvidence
from .policies import evaluate_policy_booleans, policy_e_reason


def _base(**overrides: Any) -> LeaderEvidence:
    data = dict(
        chain_continuity=True,
        bar_proximity=True,
        target_beam_context=True,
        endpoint_near_envelope=True,
        longitudinal_overlap=False,
        neighbour_ambiguity=False,
        inside_other_beam_envelope=False,
        transverse_alignment=True,
    )
    data.update(overrides)
    return LeaderEvidence(**data)


def run_unit_tests() -> Dict[str, Any]:
    tests: List[Dict[str, Any]] = []
    ev = LeaderChainEvidenceEvaluator()

    def add(tid: str, name: str, ok: bool, detail: Any = None) -> None:
        tests.append({"test_id": tid, "name": name, "pass": bool(ok), "detail": detail})

    # 1. All E conditions true -> accept
    r1 = ev.evaluate_evidence(_base())
    add(
        "UT_01",
        "all E_STRONG_COMBINED conditions true -> ACCEPT_CANDIDATE",
        r1["enhanced_decision"] == EnhancedDecision.ACCEPT_CANDIDATE.value
        and r1["policy_results"][PRODUCTION_POLICY] is True,
        r1["enhanced_reason"],
    )

    # 2. Missing chain continuity
    r2 = ev.evaluate_evidence(_base(chain_continuity=False))
    add(
        "UT_02",
        "missing chain continuity -> reject",
        r2["enhanced_decision"] == EnhancedDecision.REJECT.value
        and r2["policy_results"][PRODUCTION_POLICY] is False,
        r2["enhanced_reason"],
    )

    # 3. Missing bar proximity
    r3 = ev.evaluate_evidence(_base(bar_proximity=False))
    add(
        "UT_03",
        "missing bar proximity -> reject",
        r3["enhanced_decision"] == EnhancedDecision.REJECT.value,
        r3["enhanced_reason"],
    )

    # 4. Missing target beam context
    r4 = ev.evaluate_evidence(_base(target_beam_context=False))
    add(
        "UT_04",
        "missing target beam context -> reject",
        r4["enhanced_decision"] == EnhancedDecision.REJECT.value,
        r4["enhanced_reason"],
    )

    # 5. No endpoint and no longitudinal
    r5 = ev.evaluate_evidence(
        _base(endpoint_near_envelope=False, longitudinal_overlap=False)
    )
    add(
        "UT_05",
        "no endpoint/longitudinal evidence -> reject",
        r5["enhanced_decision"] == EnhancedDecision.REJECT.value
        and r5["enhanced_reason"]
        == "reject_missing_endpoint_or_longitudinal_evidence",
        r5["enhanced_reason"],
    )

    # 6. Neighbour ambiguity
    r6 = ev.evaluate_evidence(_base(neighbour_ambiguity=True))
    add(
        "UT_06",
        "neighbour ambiguity -> reject",
        r6["enhanced_decision"] == EnhancedDecision.REJECT.value
        and r6["enhanced_reason"] == "reject_neighbour_ambiguity",
        r6["enhanced_reason"],
    )

    # 7. Inside other beam envelope
    r7 = ev.evaluate_evidence(_base(inside_other_beam_envelope=True))
    add(
        "UT_07",
        "inside other beam envelope -> reject",
        r7["enhanced_decision"] == EnhancedDecision.REJECT.value
        and r7["enhanced_reason"] == "reject_inside_other_beam_envelope",
        r7["enhanced_reason"],
    )

    # 8. endpoint OR longitudinal behaviour
    r8a = ev.evaluate_evidence(
        _base(endpoint_near_envelope=True, longitudinal_overlap=False)
    )
    r8b = ev.evaluate_evidence(
        _base(endpoint_near_envelope=False, longitudinal_overlap=True)
    )
    r8c = ev.evaluate_evidence(
        _base(endpoint_near_envelope=False, longitudinal_overlap=False)
    )
    add(
        "UT_08",
        "endpoint OR longitudinal overlap behaviour",
        r8a["policy_results"][PRODUCTION_POLICY]
        and r8b["policy_results"][PRODUCTION_POLICY]
        and not r8c["policy_results"][PRODUCTION_POLICY],
        {
            "endpoint_only": r8a["policy_results"][PRODUCTION_POLICY],
            "longitudinal_only": r8b["policy_results"][PRODUCTION_POLICY],
            "neither": r8c["policy_results"][PRODUCTION_POLICY],
        },
    )

    # 9. Deterministic decision output
    a = ev.decide_leader(
        beam_id="B16",
        leader_id="LDR::7A1FFD68",
        stable_key="B16::LDR::7A1FFD68",
        evidence=_base(),
        current_t18_decision="REJECTED",
        current_rejection_rule="R2_LEADER_TIP",
        recovery_eligible=True,
        recovery_potential="HIGH",
    )
    b = ev.decide_leader(
        beam_id="B16",
        leader_id="LDR::7A1FFD68",
        stable_key="B16::LDR::7A1FFD68",
        evidence=_base(),
        current_t18_decision="REJECTED",
        current_rejection_rule="R2_LEADER_TIP",
        recovery_eligible=True,
        recovery_potential="HIGH",
    )
    add(
        "UT_09",
        "deterministic decision output",
        a == b
        and a["enhanced_decision"] == EnhancedDecision.ACCEPT_CANDIDATE.value
        and a["beam_ownership_written"] is False,
        a["enhanced_reason"],
    )

    # 10. B16 reference case evidence pattern (not hard-coded ID exception)
    b16_ev = LeaderEvidence(
        chain_continuity=True,
        bar_proximity=True,
        target_beam_context=True,
        endpoint_near_envelope=True,
        longitudinal_overlap=False,
        neighbour_ambiguity=False,
        inside_other_beam_envelope=False,
    )
    r10 = ev.decide_leader(
        beam_id="B16",
        leader_id="LDR::7A1FFD68",
        stable_key="B16::LDR::7A1FFD68",
        evidence=b16_ev,
        current_t18_decision="REJECTED",
        current_rejection_rule="R2_LEADER_TIP",
        recovery_eligible=True,
        recovery_potential="HIGH",
    )
    add(
        "UT_10",
        "B16 reference evidence pattern -> ACCEPT_CANDIDATE",
        r10["enhanced_decision"] == EnhancedDecision.ACCEPT_CANDIDATE.value
        and r10["enhanced_reason"]
        == "strong_chain_bar_context_with_endpoint_or_longitudinal_evidence"
        and r10["production_gate"] == ProductionGate.DIAGNOSTIC_ONLY.value,
        r10["enhanced_reason"],
    )

    # 11. Known contamination cases
    contam_cases = [
        ("neighbour", _base(neighbour_ambiguity=True)),
        ("inside", _base(inside_other_beam_envelope=True)),
        ("both", _base(neighbour_ambiguity=True, inside_other_beam_envelope=True)),
        (
            "geometry_only_no_bar",
            _base(
                bar_proximity=False,
                endpoint_near_envelope=False,
                longitudinal_overlap=True,
                transverse_alignment=True,
            ),
        ),
    ]
    contam_ok = True
    contam_detail = {}
    for name, evidence in contam_cases:
        rr = ev.evaluate_evidence(evidence)
        ok = rr["enhanced_decision"] == EnhancedDecision.REJECT.value
        contam_detail[name] = {
            "decision": rr["enhanced_decision"],
            "reason": rr["enhanced_reason"],
            "pass": ok,
        }
        contam_ok = contam_ok and ok
    add("UT_11", "known contamination / geometry-only cases rejected", contam_ok, contam_detail)

    # Extra: Policy D must not equal production accept when bar proximity false
    d_only = evaluate_policy_booleans(
        {
            "chain_continuity": True,
            "bar_proximity": False,
            "target_beam_context": True,
            "endpoint_near_envelope": False,
            "longitudinal_overlap": True,
            "transverse_alignment": True,
            "neighbour_ambiguity": False,
            "inside_other_beam_envelope": False,
        }
    )
    add(
        "UT_12",
        "Policy D geometric hit without bar proximity is not Policy E",
        d_only["D_CHAIN_GEOMETRIC"] is True and d_only[PRODUCTION_POLICY] is False,
        d_only,
    )

    # Extra: may_write_ownership false in diagnostic mode
    add(
        "UT_13",
        "diagnostic mode never writes ownership",
        ev.may_write_ownership() is False
        and ev.production_gate == ProductionGate.DIAGNOSTIC_ONLY,
    )

    # Extra: reason helper consistency
    add(
        "UT_14",
        "policy_e_reason accept string",
        policy_e_reason(_base().as_dict())
        == "strong_chain_bar_context_with_endpoint_or_longitudinal_evidence",
    )

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

    result = run_unit_tests()
    print(json.dumps({k: result[k] for k in ("overall_pass", "passed", "failed", "total", "failed_ids")}, indent=2))
    for t in result["tests"]:
        mark = "PASS" if t["pass"] else "FAIL"
        print(f"  [{mark}] {t['test_id']} {t['name']}")
    raise SystemExit(0 if result["overall_pass"] else 1)
