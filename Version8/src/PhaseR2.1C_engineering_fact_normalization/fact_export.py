"""
fact_export.py — Export all Phase R.2.1C artefacts.
MODEL_VERSION: 7.12.0

Exported artefacts:
  EngineeringFacts.json
  FactStatistics.json
  FactValidation.json
  RoleDistribution.json
  PlacementDistribution.json
  CandidateDistribution.json
  ModifierDistribution.json
  FactSummary.json
  EngineeringFactReport.json
  EngineeringFactReport.md
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
from datetime import datetime
from typing import Any, Dict, List

from .fact_models import EngineeringFact


def _dump(obj: Any, path: pathlib.Path) -> None:
    """Write JSON to path with UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, default=str)


def _fact_to_dict(fact: EngineeringFact) -> Dict[str, Any]:
    return dataclasses.asdict(fact)


class FactExport:

    def export_all(
        self,
        facts_by_beam: Dict[str, List[EngineeringFact]],
        stats: Dict[str, Any],
        validation: Dict[str, Any],
        report_md: str,
        output_dir: pathlib.Path,
    ) -> Dict[str, pathlib.Path]:
        """Export all artefacts to output_dir. Returns dict of name→path."""
        paths: Dict[str, pathlib.Path] = {}
        ts = datetime.now().isoformat()

        # Flatten facts for export
        all_facts_dicts = [
            _fact_to_dict(f)
            for fl in facts_by_beam.values()
            for f in fl
        ]
        by_beam_dicts = {
            bid: [_fact_to_dict(f) for f in fl]
            for bid, fl in facts_by_beam.items()
        }

        # EngineeringFacts.json
        p = output_dir / "EngineeringFacts.json"
        _dump({"generated_at": ts, "by_beam": by_beam_dicts, "all": all_facts_dicts}, p)
        paths["EngineeringFacts"] = p

        # FactStatistics.json
        p = output_dir / "FactStatistics.json"
        _dump({"generated_at": ts, **stats}, p)
        paths["FactStatistics"] = p

        # FactValidation.json
        p = output_dir / "FactValidation.json"
        _dump({"generated_at": ts, **validation}, p)
        paths["FactValidation"] = p

        # RoleDistribution.json
        p = output_dir / "RoleDistribution.json"
        _dump({"generated_at": ts, "role_distribution": stats.get("role_distribution", {})}, p)
        paths["RoleDistribution"] = p

        # PlacementDistribution.json
        p = output_dir / "PlacementDistribution.json"
        _dump({"generated_at": ts, "placement_distribution": stats.get("placement_distribution", {})}, p)
        paths["PlacementDistribution"] = p

        # CandidateDistribution.json
        p = output_dir / "CandidateDistribution.json"
        _dump({"generated_at": ts, "candidate_distribution": stats.get("candidate_distribution", {})}, p)
        paths["CandidateDistribution"] = p

        # ModifierDistribution.json
        p = output_dir / "ModifierDistribution.json"
        _dump({"generated_at": ts, "modifier_distribution": stats.get("modifier_distribution", {})}, p)
        paths["ModifierDistribution"] = p

        # FactSummary.json
        beam_count   = stats.get("beam_count", 0)
        total_facts  = stats.get("total_facts", 0)
        int_unknown  = stats.get("intent_unknown_count", 0)
        geo_req      = stats.get("geometry_required_count", 0)
        val_summary  = validation.get("summary", "")
        p = output_dir / "FactSummary.json"
        _dump({
            "generated_at":            ts,
            "model_version":           "7.12.0",
            "phase_id":                "R.2.1C",
            "beam_count":              beam_count,
            "total_facts":             total_facts,
            "intent_unknown_count":    int_unknown,
            "geometry_required_count": geo_req,
            "role_coverage_pct":       stats.get("role_coverage_pct", 0),
            "placement_coverage_pct":  stats.get("placement_coverage_pct", 0),
            "validation_summary":      val_summary,
            "validation_all_pass":     validation.get("all_pass", False),
        }, p)
        paths["FactSummary"] = p

        # EngineeringFactReport.json
        p = output_dir / "EngineeringFactReport.json"
        _dump({
            "generated_at": ts,
            "statistics":   stats,
            "validation":   validation,
        }, p)
        paths["EngineeringFactReport"] = p

        # EngineeringFactReport.md
        p = output_dir / "EngineeringFactReport.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            f.write(report_md)
        paths["EngineeringFactReport.md"] = p

        return paths
