"""
hypothesis_statistics.py — Statistics for Phase R.2.1D.
MODEL_VERSION: 7.12.1

Computed statistics:
  - Hypothesis frequency (how often each intent appears in ranked lists)
  - Priority distribution (what priority each intent most commonly holds)
  - Evidence distribution (zone, role_source, placement_source, r1_original_role)
  - Reason distribution (how often each reason string appears)
  - Reorder rule fire frequencies
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List

from .evidence_models import HypothesisEnrichedFact


class HypothesisStatistics:

    def compute(
        self,
        facts_by_beam: Dict[str, List[HypothesisEnrichedFact]],
        applied_rules_log: Dict[str, List[str]] = None,
    ) -> Dict[str, Any]:
        all_facts = [f for fl in facts_by_beam.values() for f in fl]
        total     = len(all_facts)

        # ── Hypothesis frequency ─────────────────────────────────────────────
        hyp_freq_ctr = Counter(
            h.intent
            for f in all_facts
            for h in f.intent_hypotheses
        )

        # ── Priority distribution per intent ─────────────────────────────────
        prio_dist: Dict[str, Counter] = defaultdict(Counter)
        for f in all_facts:
            for h in f.intent_hypotheses:
                prio_dist[h.intent][h.priority] += 1

        # Compute most common priority per intent
        top_priority_per_intent = {
            intent: ctr.most_common(1)[0][0]
            for intent, ctr in prio_dist.items()
        }

        # ── Reason distribution ───────────────────────────────────────────────
        reason_ctr = Counter(
            h.reason
            for f in all_facts
            for h in f.intent_hypotheses
        )

        # ── Evidence distribution ─────────────────────────────────────────────
        zone_ctr         = Counter()
        role_src_ctr     = Counter()
        place_src_ctr    = Counter()
        r1_role_ctr      = Counter()
        for f in all_facts:
            ev = f.observable_evidence
            if ev:
                zone_ctr[ev.annotation_zone]       += 1
                role_src_ctr[ev.role_source]       += 1
                place_src_ctr[ev.placement_source] += 1
                r1_role_ctr[ev.r1_original_role]   += 1

        # ── Reorder rules ─────────────────────────────────────────────────────
        rule_fire_ctr: Counter = Counter()
        if applied_rules_log:
            for ann_id, rules in applied_rules_log.items():
                for r in rules:
                    rule_fire_ctr[r] += 1

        # ── Per-beam hypothesis counts ────────────────────────────────────────
        per_beam = {
            bid: {"facts": len(fl), "hypotheses": sum(len(f.intent_hypotheses) for f in fl)}
            for bid, fl in facts_by_beam.items()
        }

        total_hypotheses = sum(
            len(f.intent_hypotheses) for f in all_facts
        )
        avg_hyp_per_fact = round(total_hypotheses / total, 2) if total else 0.0

        return {
            "total_facts":              total,
            "total_hypotheses":         total_hypotheses,
            "avg_hypotheses_per_fact":  avg_hyp_per_fact,
            "beam_count":               len(facts_by_beam),
            "per_beam":                 per_beam,
            "hypothesis_frequency":     dict(hyp_freq_ctr),
            "priority_distribution":    {k: dict(v) for k, v in prio_dist.items()},
            "top_priority_per_intent":  top_priority_per_intent,
            "reason_distribution":      dict(reason_ctr),
            "evidence_zone_distribution":          dict(zone_ctr),
            "evidence_role_source_distribution":   dict(role_src_ctr),
            "evidence_placement_source_distribution": dict(place_src_ctr),
            "evidence_r1_role_distribution":       dict(r1_role_ctr),
            "reorder_rule_fire_counts": dict(rule_fire_ctr),
        }
