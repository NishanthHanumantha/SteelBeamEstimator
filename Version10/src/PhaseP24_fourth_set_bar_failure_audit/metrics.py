"""
Aggregate metrics and diagnostics for P2.4.
MODEL_VERSION: 10.6.0
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Sequence

from .config import PRIORITY_BEAMS, PROBLEM_RENDER_BEAMS, RECOMMENDATION_MAP, SHARED_CASE_BEAMS


def _pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 2) if d else 0.0


def compute_metrics(
    matrix: List[Dict[str, Any]],
    extras: List[Dict[str, Any]],
    gt_registry: List[Dict[str, Any]],
) -> Dict[str, Any]:
    gt_total = len(matrix)
    matched = sum(1 for r in matrix if r["match_status"] == "MATCHED")
    partial = sum(1 for r in matrix if r["match_status"] == "PARTIALLY_MATCHED")
    unmatched = sum(1 for r in matrix if r["match_status"] == "UNMATCHED")
    extra_n = sum(1 for e in extras if e.get("status") == "EXTRA")
    acceptable_extra = sum(1 for e in extras if e.get("status") == "ACCEPTABLE_EXTRA")

    det_ok = sum(1 for r in matrix if r["physical_bar_detected"])
    own_ok = sum(1 for r in matrix if r["owned_by_correct_beam"])
    ann_ok = sum(1 for r in matrix if r["annotation_status"] == "CORRECT")
    # leader rate among rows where leader is relevant
    leader_relevant = [
        r
        for r in matrix
        if r["leader_status"] not in ("NO_LEADER_REQUIRED", "AMBIGUOUS")
        or r["leader_chain_valid"]
    ]
    leader_ok = sum(1 for r in matrix if r["leader_chain_valid"])
    role_ok = sum(1 for r in matrix if r["role_correct"])
    dia_ok = sum(1 for r in matrix if r["diameter_correct"])
    qty_ok = sum(1 for r in matrix if r["quantity_correct"])
    eng_ok = sum(1 for r in matrix if r["engineering_object_found"])
    vb1_ok = sum(1 for r in matrix if r["vb1_consumed"])
    steel_ok = sum(1 for r in matrix if r["steel_contribution_correct"])

    first_fail = Counter(r["first_failure_stage"] for r in matrix)
    # distribution among failures only
    fail_only = Counter(
        r["first_failure_stage"]
        for r in matrix
        if r["first_failure_stage"] != "NO_FAILURE"
    )
    fail_total = sum(fail_only.values()) or 1
    first_fail_pct = {
        k: round(100.0 * v / fail_total, 2) for k, v in fail_only.most_common()
    }

    # Q1-Q5 among unmatched / failing
    missing_rows = [r for r in matrix if r["match_status"] == "UNMATCHED"]
    q1 = sum(
        1
        for r in missing_rows
        if r["first_failure_stage"] == "PHYSICAL_BAR_DETECTION"
    )
    q2 = sum(1 for r in missing_rows if r["first_failure_stage"] == "OWNERSHIP")
    q3 = sum(
        1
        for r in missing_rows
        if r["first_failure_stage"] == "ANNOTATION_ASSOCIATION"
    )
    q4 = sum(
        1
        for r in missing_rows
        if r["first_failure_stage"]
        in ("ROLE_RESOLUTION", "DIAMETER_RESOLUTION", "QUANTITY_RESOLUTION")
    )
    q5 = sum(
        1
        for r in missing_rows
        if r["first_failure_stage"] in ("ENGINEERING_OBJECT", "VB1_INTEGRATION")
    )

    ranked = fail_only.most_common()
    largest = ranked[0][0] if ranked else "UNKNOWN"
    second = ranked[1][0] if len(ranked) > 1 else "NONE"
    recommendation = RECOMMENDATION_MAP.get(
        largest, "INVESTIGATE FURTHER — NO DOMINANT CATEGORY"
    )

    return {
        "gt_total_bars": gt_total,
        "matched_bars": matched,
        "partially_matched_bars": partial,
        "unmatched_gt_bars": unmatched,
        "extra_model_bars": extra_n,
        "acceptable_extra_bars": acceptable_extra,
        "physical_bar_detection_pct": _pct(det_ok, gt_total),
        "correct_beam_ownership_pct": _pct(own_ok, gt_total),
        "annotation_association_pct": _pct(ann_ok, gt_total),
        "leader_chain_success_pct": _pct(leader_ok, gt_total),
        "leader_relevant_count": len(leader_relevant),
        "role_accuracy_pct": _pct(role_ok, gt_total),
        "diameter_accuracy_pct": _pct(dia_ok, gt_total),
        "quantity_accuracy_pct": _pct(qty_ok, gt_total),
        "engineering_object_propagation_pct": _pct(eng_ok, gt_total),
        "vb1_consumption_pct": _pct(vb1_ok, gt_total),
        "final_steel_contribution_accuracy_pct": _pct(steel_ok, gt_total),
        "first_failure_counts": dict(first_fail),
        "first_failure_distribution_pct": first_fail_pct,
        "questions": {
            "Q1_missing_at_physical_detection": q1,
            "Q2_wrong_beam_ownership": q2,
            "Q3_annotation_association_fail": q3,
            "Q4_role_diameter_quantity_fail": q4,
            "Q5_engineering_or_vb1_fail": q5,
            "Q6_largest_first_fail": largest,
            "Q7_second_largest_first_fail": second,
        },
        "recommended_next_phase": recommendation,
        "top3_root_causes": [
            {"stage": k, "count": v, "pct_of_failures": first_fail_pct.get(k, 0.0)}
            for k, v in ranked[:3]
        ],
        "gt_registry_count": len(gt_registry),
    }


def beam_summaries(
    matrix: List[Dict[str, Any]],
    extras: List[Dict[str, Any]],
    required_beams: Sequence[str],
) -> List[Dict[str, Any]]:
    by_beam: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in matrix:
        by_beam[r["beam_id"]].append(r)
    extra_by: Dict[str, int] = Counter(
        e.get("beam_id") for e in extras if e.get("status") == "EXTRA"
    )

    # include required + any beam with unmatched > 0 or failure
    beam_ids = set(required_beams) | set(by_beam.keys())
    meaningful = []
    for bid in sorted(beam_ids):
        rows = by_beam.get(bid) or []
        if not rows and bid not in required_beams:
            continue
        gt_n = len(rows)
        detected = sum(1 for r in rows if r["physical_bar_detected"])
        matched = sum(1 for r in rows if r["match_status"] == "MATCHED")
        missing = sum(1 for r in rows if r["match_status"] == "UNMATCHED")
        ff = Counter(r["first_failure_stage"] for r in rows if r["first_failure_stage"] != "NO_FAILURE")
        main = ff.most_common(1)[0][0] if ff else ("NO_FAILURE" if matched == gt_n and gt_n else "UNKNOWN")
        reasons = Counter(r["failure_reason"] for r in rows if r["first_failure_stage"] != "NO_FAILURE")
        main_reason = reasons.most_common(1)[0][0] if reasons else "none"
        if gt_n == 0 and bid in required_beams:
            meaningful.append(
                {
                    "beam_id": bid,
                    "gt_bars": 0,
                    "detected": 0,
                    "matched": 0,
                    "missing": 0,
                    "extra": extra_by.get(bid, 0),
                    "detection_pct": 0.0,
                    "matching_pct": 0.0,
                    "first_failure": "ABSENT_FROM_FOURTH_SET_GT",
                    "main_failure_reason": "beam_not_in_fourth_set_estimator",
                    "in_required_list": True,
                }
            )
            continue
        if missing == 0 and matched == gt_n and bid not in required_beams and ff:
            # still include if failures (partial)
            pass
        if missing == 0 and not ff and bid not in required_beams:
            # skip perfect non-required to keep table focused — still include if extra
            if extra_by.get(bid, 0) == 0:
                continue
        meaningful.append(
            {
                "beam_id": bid,
                "gt_bars": gt_n,
                "detected": detected,
                "matched": matched,
                "missing": missing,
                "extra": extra_by.get(bid, 0),
                "detection_pct": _pct(detected, gt_n),
                "matching_pct": _pct(matched, gt_n),
                "first_failure": main,
                "main_failure_reason": main_reason,
                "in_required_list": bid in required_beams,
            }
        )
    # ensure all priority present
    have = {b["beam_id"] for b in meaningful}
    for bid in required_beams:
        if bid not in have:
            meaningful.append(
                {
                    "beam_id": bid,
                    "gt_bars": 0,
                    "detected": 0,
                    "matched": 0,
                    "missing": 0,
                    "extra": 0,
                    "detection_pct": 0.0,
                    "matching_pct": 0.0,
                    "first_failure": "ABSENT_FROM_FOURTH_SET_GT",
                    "main_failure_reason": "beam_not_in_fourth_set_estimator",
                    "in_required_list": True,
                }
            )
    meaningful.sort(key=lambda r: (0 if r["beam_id"] in required_beams else 1, r["beam_id"]))
    return meaningful


def build_diagnostics(matrix: List[Dict[str, Any]], extras: List[Dict[str, Any]]) -> Dict[str, Any]:
    def stage_diag(pred, key: str) -> Dict[str, Any]:
        rows = [r for r in matrix if pred(r)]
        return {
            "count": len(rows),
            "by_beam": dict(Counter(r["beam_id"] for r in rows).most_common(40)),
            "by_role": dict(Counter(r["gt_role"] for r in rows).most_common(20)),
            "examples": [
                {
                    "beam_id": r["beam_id"],
                    "gt_bar_id": r["gt_bar_id"],
                    "gt_role": r["gt_role"],
                    "reason": r["failure_reason"],
                    "first_failure_stage": r["first_failure_stage"],
                }
                for r in rows[:25]
            ],
            "key": key,
        }

    return {
        "detection": stage_diag(
            lambda r: r["first_failure_stage"] == "PHYSICAL_BAR_DETECTION",
            "PHYSICAL_BAR_DETECTION",
        ),
        "ownership": stage_diag(
            lambda r: r["first_failure_stage"] == "OWNERSHIP", "OWNERSHIP"
        ),
        "annotation": stage_diag(
            lambda r: r["first_failure_stage"] == "ANNOTATION_ASSOCIATION",
            "ANNOTATION_ASSOCIATION",
        ),
        "leader": stage_diag(
            lambda r: r["first_failure_stage"] == "LEADER_CHAIN", "LEADER_CHAIN"
        ),
        "role": stage_diag(
            lambda r: r["first_failure_stage"] == "ROLE_RESOLUTION", "ROLE_RESOLUTION"
        ),
        "diameter": stage_diag(
            lambda r: r["first_failure_stage"] == "DIAMETER_RESOLUTION",
            "DIAMETER_RESOLUTION",
        ),
        "quantity": stage_diag(
            lambda r: r["first_failure_stage"] == "QUANTITY_RESOLUTION",
            "QUANTITY_RESOLUTION",
        ),
        "engineering": stage_diag(
            lambda r: r["first_failure_stage"]
            in ("ENGINEERING_OBJECT", "VB1_INTEGRATION"),
            "ENGINEERING_VB1",
        ),
        "extra_bars": {
            "extra": sum(1 for e in extras if e.get("status") == "EXTRA"),
            "acceptable_extra": sum(
                1 for e in extras if e.get("status") == "ACCEPTABLE_EXTRA"
            ),
            "by_role": dict(
                Counter(
                    e.get("model_role") or e.get("bar_role")
                    for e in extras
                    if e.get("status") == "EXTRA"
                ).most_common()
            ),
            "by_beam": dict(
                Counter(
                    e.get("beam_id") for e in extras if e.get("status") == "EXTRA"
                ).most_common(40)
            ),
            "examples": extras[:40],
        },
    }


def special_analyses(
    matrix: List[Dict[str, Any]],
    beam_ids_present: Sequence[str],
    shared_scopes: Optional[Dict[str, Any]],
    shared_registry: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    present = set(beam_ids_present)
    top_rows = [r for r in matrix if r.get("is_top_reinforcement")]
    top_ff = Counter(r["first_failure_stage"] for r in top_rows)
    top_fail = Counter(
        r["first_failure_stage"]
        for r in top_rows
        if r["first_failure_stage"] != "NO_FAILURE"
    )

    problem = {}
    for bid in PROBLEM_RENDER_BEAMS:
        rows = [r for r in matrix if r["beam_id"] == bid]
        problem[bid] = {
            "present_in_fourth_set_gt": bid in present,
            "gt_bars": len(rows),
            "note": (
                "Beam ID not present in Fourth Set estimator/model registries."
                if bid not in present
                else "Present — see matrix."
            ),
            "first_failure_distribution": dict(
                Counter(r["first_failure_stage"] for r in rows)
            ),
            "conclusion": (
                "NOT_A_FOURTH_SET_BEAM — cannot attribute Fourth Set render failure to this ID."
                if bid not in present
                else "See first-failure distribution."
            ),
        }

    shared = {}
    for bid in SHARED_CASE_BEAMS:
        shared[bid] = {
            "present_in_fourth_set_gt": bid in present,
            "note": (
                "B8/B9/B10 are not Fourth Set basement beam IDs in the estimator GT."
                if bid not in present
                else "Present."
            ),
        }
    scopes = (shared_scopes or {}).get("scopes") or []
    shared["fourth_set_shared_scopes"] = scopes
    shared["shared_annotation_count"] = (shared_registry or {}).get(
        "shared_annotation_count"
    )
    shared["shared_beams_observed"] = sorted(
        {
            b
            for s in scopes
            for b in (s.get("member_beams") or [])
        }
    )
    shared["conclusion"] = (
        "Fourth Set shared-beam case is SIDE_FACE_REINFORCEMENT scope "
        f"on {shared['shared_beams_observed'] or ['(none)']}, not B8/B9/B10."
    )

    # priority beam deep dive
    priority = {}
    for bid in PRIORITY_BEAMS:
        rows = [r for r in matrix if r["beam_id"] == bid]
        ff = Counter(r["first_failure_stage"] for r in rows)
        priority[bid] = {
            "gt_bars": len(rows),
            "matched": sum(1 for r in rows if r["match_status"] == "MATCHED"),
            "unmatched": sum(1 for r in rows if r["match_status"] == "UNMATCHED"),
            "partial": sum(1 for r in rows if r["match_status"] == "PARTIALLY_MATCHED"),
            "first_failure_distribution": dict(ff),
            "dominant_first_fail": ff.most_common(1)[0][0] if ff else "UNKNOWN",
            "top_missing": sum(
                1
                for r in rows
                if r.get("is_top_reinforcement")
                and r["match_status"] == "UNMATCHED"
            ),
        }

    return {
        "top_reinforcement": {
            "gt_top_bars": len(top_rows),
            "matched": sum(1 for r in top_rows if r["match_status"] == "MATCHED"),
            "unmatched": sum(1 for r in top_rows if r["match_status"] == "UNMATCHED"),
            "first_failure_all": dict(top_ff),
            "first_failure_failures_only": dict(top_fail),
            "dominant_failure": top_fail.most_common(1)[0][0] if top_fail else "NO_FAILURE",
            "conclusion": _top_conclusion(top_fail),
        },
        "problem_beams_b10_b12_b13": problem,
        "shared_beams_b8_b9_b10": shared,
        "priority_beams": priority,
    }


def _top_conclusion(top_fail: Counter) -> str:
    if not top_fail:
        return "No top-reinforcement failures observed."
    dom, n = top_fail.most_common(1)[0]
    total = sum(top_fail.values())
    return (
        f"Missing/failing top bars are dominated by {dom} "
        f"({n}/{total} = {round(100*n/total,1)}%)."
    )
