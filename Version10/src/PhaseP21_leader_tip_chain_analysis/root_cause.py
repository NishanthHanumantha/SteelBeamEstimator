"""
Root-cause conclusions and next-phase recommendation.
MODEL_VERSION: 10.5.3
"""
from __future__ import annotations

from typing import Any, Dict, List

from .config import MODEL_VERSION, PHASE_ID


def build_root_cause(
    *,
    traces: List[Dict[str, Any]],
    scorecards: List[Dict[str, Any]],
    policies: List[Dict[str, Any]],
    comparison: Dict[str, Any],
    contam_summary: Dict[str, Any],
    impact: Dict[str, Any],
    eligible_keys: List[str],
) -> Dict[str, Any]:
    r2_reject = sum(
        1
        for t in traces
        if (t.get("existing_rejected_rule") == "R2_LEADER_TIP")
        or (t.get("exact_r2_rejection_condition") == "tip_outside_envelope_and_supports")
    )
    tip_fail = sum(1 for t in traces if t.get("r2_tip_in_envelope_ok") is False)
    strong = []
    for p in policies:
        if p.get("stable_key") not in eligible_keys:
            continue
        pr = p.get("policy_results") or {}
        if pr.get("E_STRONG_COMBINED") or pr.get("C_CHAIN_ENDPOINT"):
            strong.append(p["stable_key"])

    safe_accept_E = (
        (impact.get("potentially_recovered_leaders_by_policy_safe_only") or {}).get(
            "E_STRONG_COMBINED", 0
        )
    )
    safe_accept_C = (
        (impact.get("potentially_recovered_leaders_by_policy_safe_only") or {}).get(
            "C_CHAIN_ENDPOINT", 0
        )
    )
    safe_accept_B = (
        (impact.get("potentially_recovered_leaders_by_policy_safe_only") or {}).get(
            "B_CHAIN_EVIDENCE", 0
        )
    )

    safe_by = impact.get("potentially_recovered_leaders_by_policy_safe_only") or {}
    # Prefer strongest evidence policy that recovers >=1 SAFE eligible leader;
    # report volume leader separately for transparency.
    if safe_accept_E >= 1:
        best = "E_STRONG_COMBINED"
    elif safe_accept_C >= 1:
        best = "C_CHAIN_ENDPOINT"
    elif safe_accept_B >= 1:
        best = "B_CHAIN_EVIDENCE"
    elif (safe_by.get("D_CHAIN_GEOMETRIC") or 0) >= 1:
        best = "D_CHAIN_GEOMETRIC"
    else:
        best = "A_CURRENT"
    volume_best = max(
        (
            (safe_by.get(p) or 0, p)
            for p in (
                "E_STRONG_COMBINED",
                "C_CHAIN_ENDPOINT",
                "B_CHAIN_EVIDENCE",
                "D_CHAIN_GEOMETRIC",
                "A_CURRENT",
            )
        ),
        key=lambda x: x[0],
    )[1]

    # Q1: Is R2 too strict?
    if safe_accept_E >= 1 or safe_accept_C >= 1 or (safe_by.get("D_CHAIN_GEOMETRIC") or 0) >= 1:
        q1 = "YES"
    elif any(
        (p.get("policy_results") or {}).get("E_STRONG_COMBINED")
        for p in policies
        if p.get("stable_key") in eligible_keys
    ):
        q1 = "PARTIAL"
    else:
        q1 = "INCONCLUSIVE"

    # Q2: Is the problem the leader-tip rule?
    q2 = "YES" if tip_fail >= 20 else ("PARTIAL" if tip_fail > 0 else "NO")

    # Q3: Is the problem the production envelope?
    # Tip fails concrete+support test → envelope/support geometry is the geometric gate
    q3 = "PARTIAL" if tip_fail > 0 else "NO"

    # Q4: Does chain evidence safely recover any of the 5?
    q4 = (
        "YES"
        if safe_accept_E > 0
        or safe_accept_C > 0
        or safe_accept_B > 0
        or (safe_by.get("D_CHAIN_GEOMETRIC") or 0) > 0
        else "NO"
    )

    # Recommendation
    if safe_accept_E >= 1 or safe_accept_C >= 1:
        option = "OPTION 2 - Leader-chain evidence enhancement"
        option_id = "OPTION_2"
        rationale = (
            "Strong chain+bar+context evidence (Policy E/C) can safely recover at least "
            "the HIGH candidate without global envelope expansion. Geometric-only Policy D "
            f"recovers more volume ({safe_by.get('D_CHAIN_GEOMETRIC', 0)} SAFE) but lacks "
            "bar proximity and should not be used alone."
        )
    elif q1 == "YES" and q4 == "NO":
        option = "OPTION 5 - Do not modify T18 yet; investigate another upstream issue"
        option_id = "OPTION_5"
        rationale = "Counterfactual acceptances are contaminated or insufficient."
    elif tip_fail > 0 and safe_accept_E == 0 and (safe_by.get("D_CHAIN_GEOMETRIC") or 0) == 0:
        option = "OPTION 3 - Beam envelope/support geometry improvement"
        option_id = "OPTION_3"
        rationale = "Tips fail envelope/support geometry; investigate support extension construction."
    else:
        option = "OPTION 4 - Combination of the above"
        option_id = "OPTION_4"
        rationale = (
            "Mixed evidence: tip/support geometry fails for all 23, while chain evidence "
            "and geometric alignment recover different subsets. Coordinate tip rule, "
            "chain evidence, and envelope/support review."
        )

    # Case taxonomy for the 5
    taxonomy = []
    sc_by = {s["stable_key"]: s for s in scorecards}
    pol_by = {p["stable_key"]: p for p in policies}
    for t in traces:
        if t.get("stable_key") not in eligible_keys:
            continue
        sc = sc_by[t["stable_key"]]
        pol = pol_by[t["stable_key"]]
        pol_res = pol.get("policy_results") or {}
        # Contam status is attached later via taxonomy; use scorecard risk flags here
        contam_bad = sc.get("I_neighbour_ambiguity") or sc.get(
            "H_inside_another_beam_envelope"
        )
        would_relax = any(
            pol_res.get(p)
            for p in (
                "B_CHAIN_EVIDENCE",
                "C_CHAIN_ENDPOINT",
                "D_CHAIN_GEOMETRIC",
                "E_STRONG_COMBINED",
            )
        )
        if contam_bad:
            case = "C"  # ambiguous
        elif not sc.get("A_chain_continuity"):
            case = "D"  # broken chain
        elif would_relax and not t.get("r2_tip_in_envelope_ok") and not contam_bad:
            case = "B"  # associated with beam but rejected because R2 tip test is strict
        else:
            case = "A"  # genuinely outside / should reject
        taxonomy.append(
            {
                "stable_key": t.get("stable_key"),
                "beam_id": t.get("beam_id"),
                "leader_id": t.get("leader_id"),
                "case": case,
                "case_meaning": {
                    "A": "Leader genuinely outside / should remain rejected",
                    "B": "Associated with beam but rejected because R2 tip test is strict",
                    "C": "Ambiguous — remain rejected",
                    "D": "Leader chain broken / unreliable",
                }[case],
            }
        )

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "answers": {
            "1_is_r2_leader_tip_too_strict": q1,
            "2_is_problem_the_leader_tip_rule": q2,
            "3_is_problem_the_production_envelope": q3,
            "4_can_chain_evidence_safely_recover_any_of_5": q4,
            "5_best_policy_without_contamination": best,
            "5b_highest_volume_safe_policy": volume_best,
            "6_additional_leaders_each_policy": comparison.get("accepted_count_all_23"),
            "6b_additional_among_eligible_safe": impact.get(
                "potentially_recovered_leaders_by_policy_safe_only"
            ),
            "7_additional_annotations_reachable": impact.get(
                "potentially_recovered_annotation_count"
            ),
            "8_evidence_to_incorporate_in_future_rule": [
                "leader_chain_continuity",
                "leader_to_bar_proximity",
                "target_beam_context",
                "endpoint_near_envelope OR longitudinal_overlap",
                "explicit neighbour_ambiguity == FALSE",
                "inside_other_beam_envelope == FALSE",
            ],
            "9_evidence_not_to_use_alone": [
                "distance_to_envelope alone (arbitrary expansion)",
                "neighbour_ambiguity cases",
                "inside_other_beam_envelope",
                "far_outside spatial class",
                "points_toward_target_beam without bar proximity",
            ],
        },
        "statistics": {
            "leaders_with_r2_rejection": r2_reject,
            "tip_in_envelope_false": tip_fail,
            "contamination_counts": contam_summary.get("counts"),
            "eligible_strong_policy_hits": strong,
        },
        "case_taxonomy_for_5_candidates": taxonomy,
        "recommended_next_phase": {
            "option": option,
            "option_id": option_id,
            "rationale": rationale,
        },
        "production_fix_implemented": False,
        "label": "DIAGNOSTIC CONCLUSION — NOT A PRODUCTION RULE CHANGE",
    }
