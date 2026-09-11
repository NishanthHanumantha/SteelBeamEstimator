"""
hypothesis_export.py — Export all Phase R.2.1D artefacts.
MODEL_VERSION: 7.12.1

Exported artefacts:
  EngineeringFacts.json         — upgraded facts (with evidence + hypotheses)
  ObservableEvidence.json       — all evidence objects by beam
  IntentHypotheses.json         — all hypothesis lists by beam
  HypothesisStatistics.json     — full statistics
  PriorityDistribution.json     — per-intent priority distributions
  ReasonDistribution.json       — hypothesis reason frequencies
  EvidenceDistribution.json     — evidence zone/source distributions
  HypothesisValidation.json     — 12-rule validation results
  EngineeringHypothesisReport.json — full report in JSON
  EngineeringHypothesisReport.md   — Markdown report
  FactSummary.json              — concise summary
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
from datetime import datetime
from typing import Any, Dict, List

from .evidence_models import HypothesisEnrichedFact, ObservableEvidence, IntentHypothesis


def _dump(obj: Any, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, default=str)


def _fact_to_dict(fact: HypothesisEnrichedFact) -> Dict[str, Any]:
    """Serialize HypothesisEnrichedFact to a JSON-compatible dict."""
    ev = fact.observable_evidence
    ev_dict = dataclasses.asdict(ev) if ev else {}
    hyp_list = [
        {"intent": h.intent, "priority": h.priority, "reason": h.reason}
        for h in fact.intent_hypotheses
    ]
    return {
        "annotation_id":           fact.annotation_id,
        "beam_id":                 fact.beam_id,
        "clean_text":              fact.clean_text,
        "quantity":                fact.quantity,
        "diameter":                fact.diameter,
        "grade":                   fact.grade,
        "spacing":                 fact.spacing,
        "role":                    fact.role,
        "placement":               fact.placement,
        "intent":                  fact.intent,
        "observable_evidence":     ev_dict,
        "intent_hypotheses":       hyp_list,
        "intent_candidates":       fact.intent_candidates,
        "modifiers":               fact.modifiers,
        "semantic_flags":          fact.semantic_flags,
        "confidence":              fact.confidence,
        "source":                  fact.source,
        "engineering_notes":       fact.engineering_notes,
        "geometry_required":       fact.geometry_required,
        "intent_deferred_reason":  fact.intent_deferred_reason,
    }


class HypothesisExport:

    def export_all(
        self,
        facts_by_beam: Dict[str, List[HypothesisEnrichedFact]],
        stats:         Dict[str, Any],
        validation:    Dict[str, Any],
        report_md:     str,
        output_dir:    pathlib.Path,
    ) -> Dict[str, pathlib.Path]:
        paths: Dict[str, pathlib.Path] = {}
        ts = datetime.now().isoformat()

        all_fact_dicts = [
            _fact_to_dict(f)
            for fl in facts_by_beam.values()
            for f in fl
        ]
        by_beam_dicts = {
            bid: [_fact_to_dict(f) for f in fl]
            for bid, fl in facts_by_beam.items()
        }

        # EngineeringFacts.json — full upgraded facts
        p = output_dir / "EngineeringFacts.json"
        _dump({"generated_at": ts, "by_beam": by_beam_dicts, "all": all_fact_dicts}, p)
        paths["EngineeringFacts"] = p

        # ObservableEvidence.json
        ev_by_beam = {
            bid: [
                dataclasses.asdict(f.observable_evidence)
                for f in fl
                if f.observable_evidence
            ]
            for bid, fl in facts_by_beam.items()
        }
        p = output_dir / "ObservableEvidence.json"
        _dump({"generated_at": ts, "by_beam": ev_by_beam}, p)
        paths["ObservableEvidence"] = p

        # IntentHypotheses.json
        hyp_by_beam = {
            bid: [
                {
                    "annotation_id": f.annotation_id,
                    "clean_text":    f.clean_text,
                    "role":          f.role,
                    "placement":     f.placement,
                    "hypotheses": [
                        {"intent": h.intent, "priority": h.priority, "reason": h.reason}
                        for h in f.intent_hypotheses
                    ],
                }
                for f in fl
            ]
            for bid, fl in facts_by_beam.items()
        }
        p = output_dir / "IntentHypotheses.json"
        _dump({"generated_at": ts, "by_beam": hyp_by_beam}, p)
        paths["IntentHypotheses"] = p

        # HypothesisStatistics.json
        p = output_dir / "HypothesisStatistics.json"
        _dump({"generated_at": ts, **stats}, p)
        paths["HypothesisStatistics"] = p

        # PriorityDistribution.json
        p = output_dir / "PriorityDistribution.json"
        _dump({
            "generated_at": ts,
            "priority_distribution":   stats.get("priority_distribution", {}),
            "top_priority_per_intent": stats.get("top_priority_per_intent", {}),
        }, p)
        paths["PriorityDistribution"] = p

        # ReasonDistribution.json
        p = output_dir / "ReasonDistribution.json"
        _dump({"generated_at": ts, "reason_distribution": stats.get("reason_distribution", {})}, p)
        paths["ReasonDistribution"] = p

        # EvidenceDistribution.json
        p = output_dir / "EvidenceDistribution.json"
        _dump({
            "generated_at": ts,
            "zone_distribution":             stats.get("evidence_zone_distribution", {}),
            "role_source_distribution":      stats.get("evidence_role_source_distribution", {}),
            "placement_source_distribution": stats.get("evidence_placement_source_distribution", {}),
            "r1_role_distribution":          stats.get("evidence_r1_role_distribution", {}),
        }, p)
        paths["EvidenceDistribution"] = p

        # HypothesisValidation.json
        p = output_dir / "HypothesisValidation.json"
        _dump({"generated_at": ts, **validation}, p)
        paths["HypothesisValidation"] = p

        # EngineeringHypothesisReport.json
        p = output_dir / "EngineeringHypothesisReport.json"
        _dump({"generated_at": ts, "statistics": stats, "validation": validation}, p)
        paths["EngineeringHypothesisReport"] = p

        # EngineeringHypothesisReport.md
        p = output_dir / "EngineeringHypothesisReport.md"
        with p.open("w", encoding="utf-8") as f:
            f.write(report_md)
        paths["EngineeringHypothesisReport.md"] = p

        # FactSummary.json
        p = output_dir / "FactSummary.json"
        _dump({
            "generated_at":            ts,
            "model_version":           "7.12.1",
            "phase_id":                "R.2.1D",
            "beam_count":              stats.get("beam_count", 0),
            "total_facts":             stats.get("total_facts", 0),
            "total_hypotheses":        stats.get("total_hypotheses", 0),
            "avg_hypotheses_per_fact": stats.get("avg_hypotheses_per_fact", 0),
            "reorder_rules_applied":   stats.get("reorder_rule_fire_counts", {}),
            "validation_summary":      validation.get("summary", ""),
            "validation_all_pass":     validation.get("all_pass", False),
        }, p)
        paths["FactSummary"] = p

        return paths
