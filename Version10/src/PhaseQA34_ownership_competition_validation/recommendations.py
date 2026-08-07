"""
Engineering recommendations from competition evidence only.
MODEL_VERSION: 10.0.4
"""
from __future__ import annotations

from typing import Any, Dict, List


def build_recommendations(
    global_stats: Dict[str, Any], beam_summaries: List[Dict[str, Any]]
) -> Dict[str, Any]:
    dropped = int(global_stats.get("dropped") or 0)
    owned_else = int(global_stats.get("owned_elsewhere") or 0)
    leader = int(global_stats.get("leader_failures") or 0)
    geom = int(global_stats.get("geometry_failures") or 0)
    env = int(global_stats.get("envelope_failures") or 0)
    conflict = int(global_stats.get("conflict_failures") or 0)
    total = max(int(global_stats.get("total_rejected") or 0), 1)

    # Dominant target for QA.4.0
    scores = {
        "neighbour_ownership_or_conflict": conflict + owned_else,
        "leader_association": leader,
        "geometry": geom,
        "search_envelope": env,
        "dropped_disappearance": dropped,
    }
    dominant = max(scores.items(), key=lambda kv: kv[1])

    if dropped >= owned_else and dropped / total >= 0.4:
        p1 = {
            "priority": 1,
            "title": "Target disappearing entities (Dropped), not only R5",
            "recommendation": (
                "A large share of rejects are Owned nowhere (Dropped). "
                "QA.4.0 must not assume neighbour ownership transfers — many entities "
                "simply disappear. Focus root-cause work on DroppedEntities.json "
                f"(leader={leader}, geometry={geom}, envelope={env}, conflict-marked-dropped "
                f"subset inside conflict_failures={conflict})."
            ),
            "qa40_target": "dropped_entity_recovery",
            "engineering_impact": "High",
            "expected_benchmark_improvement": (
                "Recover callouts/bars that currently vanish from all beam ownership sets"
            ),
            "evidence": {
                "dropped": dropped,
                "owned_elsewhere": owned_else,
                "dropped_fraction": global_stats.get("dropped_fraction_of_rejects"),
            },
        }
    elif owned_else > dropped:
        p1 = {
            "priority": 1,
            "title": "Target legitimate neighbour ownership / competition",
            "recommendation": (
                "Most rejects are OwnedElsewhere — another beam legitimately won. "
                "QA.4.0 should tune competition / neighbour rules using recorded margins, "
                "not blanket R5 removal."
            ),
            "qa40_target": "neighbour_ownership",
            "engineering_impact": "High",
            "expected_benchmark_improvement": (
                "Reduce false rejects where a neighbour already owns the entity"
            ),
            "evidence": {
                "owned_elsewhere": owned_else,
                "average_margin": global_stats.get("average_ownership_margin"),
            },
        }
    else:
        p1 = {
            "priority": 1,
            "title": f"Target dominant failure mode: {dominant[0]}",
            "recommendation": (
                f"Competition validation shows dominant signal `{dominant[0]}` "
                f"(count={dominant[1]}). Use DroppedEntities.json and "
                "OwnershipMigration.json to drive QA.4.0 — not heuristic R5-only fixes."
            ),
            "qa40_target": dominant[0],
            "engineering_impact": "High",
            "expected_benchmark_improvement": "Evidence-led ownership recall/precision gains",
            "evidence": scores,
        }

    # Second priority by subtype among dropped
    subtype = max(
        [
            ("leader_association", leader),
            ("geometry", geom),
            ("search_envelope", env),
        ],
        key=lambda kv: kv[1],
    )
    p2 = {
        "priority": 2,
        "title": f"Secondary target: {subtype[0]}",
        "recommendation": (
            f"Among Dropped/failure subtypes, `{subtype[0]}` leads with {subtype[1]} cases. "
            "Instrument QA.4.0 changes against EntityDecisionTrace + this competition registry."
        ),
        "qa40_target": subtype[0],
        "engineering_impact": "Medium-High",
        "expected_benchmark_improvement": f"Reduce {subtype[0]} driven drops",
        "evidence": {"subtype_counts": dict([("leader", leader), ("geometry", geom), ("envelope", env)])},
    }
    p3 = {
        "priority": 3,
        "title": "Keep competition regression gates",
        "recommendation": (
            "Any QA.4.0 ownership change must re-run QA.3.4 and show an intentional "
            "diff in Dropped vs OwnedElsewhere — never silent decision changes."
        ),
        "qa40_target": "process_gate",
        "engineering_impact": "Medium",
        "expected_benchmark_improvement": "Prevents opaque ownership regressions",
        "evidence": {"total_rejected": total},
    }

    return {
        "priorities": [p1, p2, p3],
        "dominant_qa40_target": p1.get("qa40_target"),
        "summary": (
            f"rejected={total} owned_elsewhere={owned_else} dropped={dropped} "
            f"leader={leader} geometry={geom} envelope={env} conflict={conflict}; "
            f"dominant={p1.get('qa40_target')}"
        ),
        "mode_scores": scores,
    }
