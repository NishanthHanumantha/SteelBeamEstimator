"""
Failure pattern clustering + representative case selection + priority matrix.
MODEL_VERSION: 10.5.0
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Sequence

MODEL_VERSION = "10.5.0"


def cluster_patterns(audits: List[Dict[str, Any]]) -> Dict[str, Any]:
    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for a in audits:
        cat = a.get("primary_audit_category")
        pot = a.get("recovery_potential")
        env = a.get("envelope_audit") or {}
        sp = env.get("spatial_relationship")
        leader = a.get("leader_audit") or {}
        geom = a.get("geometry_audit") or {}
        flags = a.get("evidence_flags") or {}

        if cat == "ENVELOPE_NEVER_CANDIDATE" and sp == "NEAR_OUTSIDE" and pot == "HIGH":
            pid = "PATTERN-01"
            desc = "Entity barely outside production envelope (NEAR_OUTSIDE, HIGH potential)"
        elif cat == "ENVELOPE_NEVER_CANDIDATE" and flags.get("neighbour_ambiguity"):
            pid = "PATTERN-06"
            desc = "Entity lies between / closer to neighbouring beams"
        elif cat == "ENVELOPE_NEVER_CANDIDATE" and sp == "FAR_OUTSIDE":
            pid = "PATTERN-08"
            desc = "Entity far outside target beam context"
        elif cat == "ENVELOPE_NEVER_CANDIDATE" and a.get("same_annotation_text_on_other_beams"):
            pid = "PATTERN-07"
            desc = "Same annotation text appears on multiple beams (but Dropped locally)"
        elif cat == "ENVELOPE_NEVER_CANDIDATE":
            pid = "PATTERN-01B"
            desc = "Envelope never-candidate (other spatial band)"
        elif cat == "LEADER_CHAIN_FAILURE" and leader.get("failure_class") == "LEADER_TIP_OUTSIDE" and pot == "HIGH":
            pid = "PATTERN-03"
            desc = "Leader tip outside envelope while near production zone"
        elif cat == "LEADER_CHAIN_FAILURE" and leader.get("failure_class") in (
            "LEADER_CHAIN_DISCONNECTED",
            "LEADER_CHAIN_INCOMPLETE",
        ):
            pid = "PATTERN-04"
            desc = "Leader chain broken / incomplete"
        elif cat == "LEADER_CHAIN_FAILURE":
            pid = "PATTERN-02"
            desc = "Leader-chain failure with directional/context evidence"
        elif cat == "GEOMETRY_FAILURE" and geom.get("geometry_class") in (
            "ZERO_WIDTH",
            "ZERO_HEIGHT",
            "DEGENERATE",
        ):
            pid = "PATTERN-05B"
            desc = "Degenerate / zero-dimension geometry"
        elif cat == "GEOMETRY_FAILURE":
            pid = "PATTERN-05"
            desc = "Geometry valid-ish but geometry ownership test fails"
        else:
            pid = "PATTERN-09"
            desc = "Other / unclassified dropped pattern"

        buckets[pid].append({**a, "pattern_id": pid, "pattern_description": desc})

    n = max(len(audits), 1)
    patterns = []
    for pid, items in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        desc = items[0].get("pattern_description")
        cats = Counter(i.get("primary_audit_category") for i in items)
        pots = Counter(i.get("recovery_potential") for i in items)
        beams = sorted({i.get("beam_id") for i in items})
        primary_cat = cats.most_common(1)[0][0]
        # recommended mechanism
        if primary_cat == "ENVELOPE_NEVER_CANDIDATE":
            mech = "candidate_search_envelope_recovery"
        elif primary_cat == "LEADER_CHAIN_FAILURE":
            mech = "leader_chain_recovery"
        elif primary_cat == "GEOMETRY_FAILURE":
            mech = "geometry_recovery"
        else:
            mech = "investigate_further"
        # recovery potential of pattern
        if pots.get("HIGH", 0) >= max(1, len(items) // 3):
            ppot = "HIGH"
        elif pots.get("MEDIUM", 0) + pots.get("HIGH", 0) >= len(items) // 2:
            ppot = "MEDIUM"
        else:
            ppot = "LOW"
        patterns.append(
            {
                "pattern_id": pid,
                "description": desc,
                "entity_count": len(items),
                "percentage_of_dropped": round(100.0 * len(items) / n, 2),
                "affected_beams": beams,
                "primary_failure_category": primary_cat,
                "recovery_potential": ppot,
                "potential_breakdown": dict(pots),
                "representative_entities": [
                    {
                        "beam_id": i.get("beam_id"),
                        "entity_id": i.get("entity_id"),
                        "text": i.get("text"),
                        "recovery_potential": i.get("recovery_potential"),
                    }
                    for i in items[:5]
                ],
                "recommended_future_recovery_mechanism": mech,
            }
        )
        # stamp pattern onto audits via return mapping
    # apply pattern ids back
    pattern_of = {}
    for pid, items in buckets.items():
        for i in items:
            pattern_of[i["stable_key"]] = {
                "pattern_id": pid,
                "pattern_description": i.get("pattern_description"),
            }

    return {"patterns": patterns, "pattern_of": pattern_of}


def select_representatives(audits: List[Dict[str, Any]]) -> Dict[str, Any]:
    def pick(cat: str, pot: str, n: int) -> List[Dict[str, Any]]:
        pool = [
            a
            for a in audits
            if a.get("primary_audit_category") == cat and a.get("recovery_potential") == pot
        ]
        return [
            {
                "beam_id": a["beam_id"],
                "entity_id": a["entity_id"],
                "text": a.get("text"),
                "primary_audit_category": a.get("primary_audit_category"),
                "recovery_potential": a.get("recovery_potential"),
                "reason": a.get("original_rejection_reason"),
                "spatial_relationship": (a.get("envelope_audit") or {}).get("spatial_relationship"),
                "min_distance_to_production_envelope": (a.get("envelope_audit") or {}).get(
                    "min_distance_to_production_envelope"
                ),
                "leader_failure_class": (a.get("leader_audit") or {}).get("failure_class"),
                "geometry_class": (a.get("geometry_audit") or {}).get("geometry_class"),
                "requested": n,
                "available": len(pool),
            }
            for a in pool[:n]
        ]

    env_high = pick("ENVELOPE_NEVER_CANDIDATE", "HIGH", 5)
    env_med = pick("ENVELOPE_NEVER_CANDIDATE", "MEDIUM", 5)
    env_low = pick("ENVELOPE_NEVER_CANDIDATE", "LOW", 5)
    ldr_high = pick("LEADER_CHAIN_FAILURE", "HIGH", 5)
    ldr_other = [
        a
        for a in audits
        if a.get("primary_audit_category") == "LEADER_CHAIN_FAILURE"
        and a.get("recovery_potential") in ("MEDIUM", "LOW")
    ][:5]
    ldr_other_rows = [
        {
            "beam_id": a["beam_id"],
            "entity_id": a["entity_id"],
            "text": a.get("text"),
            "primary_audit_category": a.get("primary_audit_category"),
            "recovery_potential": a.get("recovery_potential"),
            "leader_failure_class": (a.get("leader_audit") or {}).get("failure_class"),
            "requested": 5,
            "available": len(
                [
                    x
                    for x in audits
                    if x.get("primary_audit_category") == "LEADER_CHAIN_FAILURE"
                    and x.get("recovery_potential") in ("MEDIUM", "LOW")
                ]
            ),
        }
        for a in ldr_other
    ]
    geom_all = [
        {
            "beam_id": a["beam_id"],
            "entity_id": a["entity_id"],
            "text": a.get("text"),
            "primary_audit_category": a.get("primary_audit_category"),
            "recovery_potential": a.get("recovery_potential"),
            "geometry_class": (a.get("geometry_audit") or {}).get("geometry_class"),
            "reason": a.get("original_rejection_reason"),
        }
        for a in audits
        if a.get("primary_audit_category") == "GEOMETRY_FAILURE"
    ]

    return {
        "envelope_high": env_high,
        "envelope_medium": env_med,
        "envelope_low": env_low,
        "leader_high": ldr_high,
        "leader_medium_low": ldr_other_rows,
        "geometry_all": geom_all,
        "counts": {
            "envelope_high": len(env_high),
            "envelope_medium": len(env_med),
            "envelope_low": len(env_low),
            "leader_high": len(ldr_high),
            "leader_medium_low": len(ldr_other_rows),
            "geometry_all": len(geom_all),
        },
        "note": "If fewer than requested, all available cases are included.",
    }


def build_priority_matrix(
    audits: List[Dict[str, Any]], patterns: List[Dict[str, Any]]
) -> Dict[str, Any]:
    n = max(len(audits), 1)
    rows = []
    for cat, label, mech, complexity, risk in [
        (
            "ENVELOPE_NEVER_CANDIDATE",
            "Candidate / Search Envelope",
            "candidate_search_envelope_recovery",
            "Medium",
            "Medium — near-neighbour entities must stay filtered",
        ),
        (
            "LEADER_CHAIN_FAILURE",
            "Leader Chain",
            "leader_chain_recovery",
            "Medium-High",
            "Medium — tip may point at neighbour reinforcement",
        ),
        (
            "GEOMETRY_FAILURE",
            "Geometry",
            "geometry_recovery",
            "High",
            "Low-Medium — small population",
        ),
        (
            "OTHER_UNKNOWN",
            "Other / Unknown",
            "investigate_further",
            "Unknown",
            "Unknown",
        ),
    ]:
        items = [a for a in audits if a.get("primary_audit_category") == cat]
        pots = Counter(a.get("recovery_potential") for a in items)
        high = pots.get("HIGH", 0)
        # expected opportunity
        opportunity = "High" if high >= 3 or len(items) >= 50 else (
            "Medium" if len(items) >= 10 else "Low"
        )
        rows.append(
            {
                "failure_category": cat,
                "label": label,
                "entity_count": len(items),
                "pct_of_dropped": round(100.0 * len(items) / n, 2),
                "high_potential": pots.get("HIGH", 0),
                "medium_potential": pots.get("MEDIUM", 0),
                "low_potential": pots.get("LOW", 0),
                "unknown_potential": pots.get("UNKNOWN", 0),
                "representative_cases": [
                    f"{a['beam_id']}:{a['entity_id']}" for a in items[:5]
                ],
                "expected_recovery_opportunity": opportunity,
                "engineering_complexity": complexity,
                "risk_of_neighbour_contamination": risk,
                "recommended_mechanism": mech,
            }
        )

    # Priority order by (count * weight of HIGH)
    def score(r):
        return r["entity_count"] * 1.0 + r["high_potential"] * 2.0

    ordered = sorted(
        [r for r in rows if r["entity_count"] > 0],
        key=score,
        reverse=True,
    )
    for i, r in enumerate(ordered, start=1):
        r["priority"] = f"P{i}"
    # attach priority onto all rows
    pmap = {r["failure_category"]: r.get("priority") for r in ordered}
    for r in rows:
        r["priority"] = pmap.get(r["failure_category"]) or "P-"

    return {
        "rows": rows,
        "recommended_sequence": [
            r["recommended_mechanism"] for r in ordered
        ]
        + [
            "full_qa4_recovery_benchmark",
            "fifth_sixth_set_generalization_validation",
        ],
        "evidence_driven_p1": (ordered[0]["failure_category"] if ordered else None),
    }


def build_recommendations(
    audits: List[Dict[str, Any]],
    matrix: Dict[str, Any],
    representatives: Dict[str, Any],
) -> Dict[str, Any]:
    n = len(audits)
    cats = Counter(a.get("primary_audit_category") for a in audits)
    env = cats.get("ENVELOPE_NEVER_CANDIDATE", 0)
    ldr = cats.get("LEADER_CHAIN_FAILURE", 0)
    geom = cats.get("GEOMETRY_FAILURE", 0)
    env_items = [a for a in audits if a.get("primary_audit_category") == "ENVELOPE_NEVER_CANDIDATE"]
    ldr_items = [a for a in audits if a.get("primary_audit_category") == "LEADER_CHAIN_FAILURE"]
    dists = [
        (a.get("envelope_audit") or {}).get("min_distance_to_production_envelope")
        for a in env_items
        if (a.get("envelope_audit") or {}).get("min_distance_to_production_envelope") is not None
    ]
    env_high = sum(1 for a in env_items if a.get("recovery_potential") == "HIGH")
    ldr_high = sum(1 for a in ldr_items if a.get("recovery_potential") == "HIGH")
    spatial = Counter(
        (a.get("envelope_audit") or {}).get("spatial_relationship") for a in env_items
    )

    p1 = (matrix.get("evidence_driven_p1") or "ENVELOPE_NEVER_CANDIDATE")
    return {
        "answers": {
            "1_envelope_problems": env,
            "2_leader_chain_problems": ldr,
            "3_geometry_problems": geom,
            "4_envelope_distance_stats": {
                "count_with_distance": len(dists),
                "min": min(dists) if dists else None,
                "max": max(dists) if dists else None,
                "avg": round(sum(dists) / len(dists), 3) if dists else None,
                "spatial_relationship_counts": dict(spatial),
            },
            "5_envelope_high_potential": env_high,
            "6_leader_high_potential": ldr_high,
            "7_dominant_patterns": [
                r.get("pattern_id")
                for r in []  # filled by orchestrator
            ],
            "8_first_recovery_mechanism": (
                "candidate_search_envelope_recovery"
                if p1 == "ENVELOPE_NEVER_CANDIDATE"
                else "leader_chain_recovery"
                if p1 == "LEADER_CHAIN_FAILURE"
                else "geometry_recovery"
            ),
            "9_representative_cases_for_first_impl": representatives.get("envelope_high")
            or representatives.get("leader_high"),
            "10_neighbour_contamination_risks": (
                "Recovering NEAR_OUTSIDE entities that are closer to a neighbour envelope, "
                "or leaders with LEADER_TARGET_NEIGHBOUR failure class, can import "
                "neighbour reinforcement. Keep 'recover candidates, then let ownership decide'."
            ),
        },
        "principle": "Recover candidates, then let the existing ownership engine decide.",
        "next_implementation_sequence": [
            "1. Candidate / Search Envelope Recovery",
            "2. Leader Chain Recovery",
            "3. Geometry Recovery",
            "4. Full QA.4 recovery benchmark",
            "5. Fifth/Sixth Set generalization validation",
        ],
        "priorities": [
            {
                "priority": 1,
                "title": "Candidate / Search Envelope Recovery",
                "recommendation": (
                    f"{env}/{n} dropped entities never became candidates. "
                    f"{env_high} rated HIGH potential (barely outside production envelope). "
                    "Implement a diagnostic recovery envelope only after validating "
                    "representative HIGH cases — do not change ownership rules first."
                ),
                "evidence": {"envelope": env, "high": env_high, "spatial": dict(spatial)},
            },
            {
                "priority": 2,
                "title": "Leader Chain Recovery",
                "recommendation": (
                    f"{ldr}/{n} leader-chain failures; {ldr_high} HIGH potential. "
                    "Focus on LEADER_TIP_OUTSIDE cases near the production envelope."
                ),
                "evidence": {"leader": ldr, "high": ldr_high},
            },
            {
                "priority": 3,
                "title": "Geometry Recovery",
                "recommendation": (
                    f"Only {geom} geometry failures. Inspect all cases before any geometry-rule change."
                ),
                "evidence": {"geometry": geom},
            },
        ],
    }
