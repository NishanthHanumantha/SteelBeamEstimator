"""
Stage 7 — Global analysis + recommendations.
MODEL_VERSION: 10.0.3
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


def _avg(vals: List[float]) -> float:
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def aggregate(
    records: List[Dict[str, Any]], competition_index: Dict[str, Any]
) -> Dict[str, Any]:
    fail_freq = Counter()
    reject_reasons = Counter()
    filter_rules = Counter()
    discovery_rates = []
    rejection_rates = []
    acceptance_rates = []
    conflict_freqs = []
    accepted_scores = []
    rejected_scores = []
    margins = []

    for r in records:
        fc = (r.get("stage6_failure_classification") or {}).get("primary_cause") or "Mixed"
        fail_freq[fc] += 1
        for reason, n in (
            (r.get("stage6_failure_classification") or {}).get("rejection_reason_counts") or {}
        ).items():
            reject_reasons[str(reason)] += int(n)

        cov = r.get("stage5_coverage") or {}
        inside = max(int(cov.get("entities_inside_search_envelope") or 0), 1)
        considered = int(cov.get("entities_considered") or 0)
        scored = max(int(cov.get("entities_scored") or 0), 1)
        owned = int(cov.get("entities_owned") or 0)
        rejected = int(cov.get("entities_rejected") or 0)
        discovery_rates.append(100.0 * considered / inside)
        rejection_rates.append(100.0 * rejected / scored)
        acceptance_rates.append(100.0 * owned / scored)
        conflict_freqs.append(float(cov.get("conflict_pct") or 0.0))

        for s in (r.get("stage2_ownership_scoring") or {}).get("t18_scored_entities") or []:
            sc = s.get("total_ownership_score")
            if sc is None:
                continue
            if s.get("accepted"):
                accepted_scores.append(float(sc))
            else:
                rejected_scores.append(float(sc))
            if s.get("rejected_rule"):
                filter_rules[str(s.get("rejected_rule"))] += 1

        by_ent = ((r.get("stage3_competing_beams") or {}).get("by_entity") or {})
        for c in by_ent.values():
            if isinstance(c, dict) and c.get("margin") is not None:
                margins.append(float(c["margin"]))

    # Competing scenario (prefer annotation-text collisions; entity ids are beam-local)
    multi_scenarios = Counter()
    for text, c in (competition_index.get("by_annotation_text") or {}).items():
        beams = c.get("considered_by") or []
        if len(beams) >= 2:
            key = f"{text}::{'+'.join(sorted(beams)[:4])}"
            multi_scenarios[key] += 1
    if not multi_scenarios:
        for eid, c in (competition_index.get("by_entity") or {}).items():
            if not c.get("in_priority_set"):
                continue
            if len(c.get("competing_beams") or []) >= 2:
                key = "+".join(sorted(c["competing_beams"][:4]))
                multi_scenarios[key] += 1

    n = len(records)
    return {
        "beams_analysed": n,
        "candidate_discovery_rate": _avg(discovery_rates),
        "candidate_rejection_rate": _avg(rejection_rates),
        "ownership_acceptance_rate": _avg(acceptance_rates),
        "conflict_frequency": _avg(conflict_freqs),
        "average_competing_beams_per_entity": competition_index.get(
            "average_competing_beams"
        ),
        "multi_beam_entity_count": competition_index.get("multi_beam_entity_count"),
        "multi_beam_annotation_text_count": competition_index.get(
            "multi_beam_annotation_text_count"
        ),
        "average_ownership_score": _avg(accepted_scores),
        "average_rejection_score": _avg(rejected_scores),
        "average_score_margin": _avg(margins),
        "failure_frequency_by_category": dict(fail_freq),
        "most_common_rejection_reason": (
            reject_reasons.most_common(1)[0] if reject_reasons else None
        ),
        "most_common_competing_beam_scenario": (
            multi_scenarios.most_common(1)[0] if multi_scenarios else None
        ),
        "most_common_filtering_rule": (
            filter_rules.most_common(1)[0] if filter_rules else None
        ),
        "top_rejection_reasons": reject_reasons.most_common(10),
        "top_filtering_rules": filter_rules.most_common(10),
        "top_competing_scenarios": multi_scenarios.most_common(10),
        "top_failure_categories": fail_freq.most_common(),
    }


def build_recommendations(agg: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
    top_fail = (agg.get("top_failure_categories") or [("Mixed", 0)])[0]
    top_reason = agg.get("most_common_rejection_reason")
    top_rule = agg.get("most_common_filtering_rule")

    # Map dominant failure to engineering priority (no code changes)
    cause = top_fail[0] if top_fail else "Mixed"

    if cause in ("Conflict Resolution",):
        p1_title = "Neighbour / conflict resolution rules (R5)"
        p1_rec = (
            "Most ownership shortfalls are neighbour-side rejects or multi-beam "
            "competition. QA.4.0 should focus on R5_NEIGHBOUR_REJECT / side_of_mark "
            "logic using these decision traces — without guessing."
        )
        impact = "High"
        bench = "Expected: reduce false neighbour rejects; improve bar/annotation match on stacked beams"
    elif cause in ("Search Envelope",):
        p1_title = "Ownership search envelope geometry"
        p1_rec = (
            "Entities are excluded by envelope bands (concrete / annotation_reach). "
            "QA.4.0 should tune envelope constants using measured miss distances from Stage 1."
        )
        impact = "High"
        bench = "Expected: increase candidate coverage for callouts just outside reach"
    elif cause in ("Annotation Dependency",):
        p1_title = "Leader→Bar→Annotation chain ownership"
        p1_rec = (
            "Rejects are dominated by missing or broken annotation chains. "
            "Improve chain association / tip-to-bar linking before changing scores."
        )
        impact = "High"
        bench = "Expected: recover callouts that have geometry but fail R3 chain rule"
    elif cause in ("Candidate Filtering", "Candidate Discovery"):
        p1_title = "Candidate discovery / pre-score filtering"
        p1_rec = (
            "Many nearby entities never enter T18 scoring. Trace graph indexing and "
            "type filters before altering score weights."
        )
        impact = "Medium-High"
        bench = "Expected: more candidates scored; possible ownership recall gains"
    else:
        p1_title = "Ownership scoring transparency follow-through"
        p1_rec = (
            "Use EntityDecisionTrace.json to target the dominant rejection reasons "
            f"({top_reason}) and filtering rules ({top_rule})."
        )
        impact = "Medium"
        bench = "Expected: incremental ownership precision/recall improvements"

    p1 = {
        "priority": 1,
        "title": p1_title,
        "recommendation": p1_rec,
        "engineering_impact": impact,
        "expected_benchmark_improvement": bench,
        "evidence": {
            "top_failure_category": top_fail,
            "most_common_rejection_reason": top_reason,
            "most_common_filtering_rule": top_rule,
            "ownership_acceptance_rate": agg.get("ownership_acceptance_rate"),
        },
    }
    p2 = {
        "priority": 2,
        "title": "Preserve decision-trace regression gates in QA.4.0",
        "recommendation": (
            "Any ownership change must keep EntityDecisionTrace outcomes explainable "
            "and must not silently alter decisions without a before/after trace diff."
        ),
        "engineering_impact": "Medium",
        "expected_benchmark_improvement": "Process quality; prevents opaque regressions",
        "evidence": {"beams_analysed": agg.get("beams_analysed")},
    }
    p3 = {
        "priority": 3,
        "title": "Separate Manual-crop GT issues (QA.3.2) from Ownership defects",
        "recommendation": (
            "QA.3.2 showed Manual crops are unreliable. Ownership improvements should "
            "be validated against decision traces and entity registries, not Manual PNG IoU alone."
        ),
        "engineering_impact": "Medium",
        "expected_benchmark_improvement": "Cleaner measurement of true ownership gains",
        "evidence": {
            "conflict_frequency": agg.get("conflict_frequency"),
            "average_score_margin": agg.get("average_score_margin"),
        },
    }
    return {
        "priorities": [p1, p2, p3],
        "summary": (
            f"top_fail={top_fail}; top_reject={top_reason}; top_rule={top_rule}; "
            f"accept_rate={agg.get('ownership_acceptance_rate')}"
        ),
    }
