"""
Phase QA.1.1 — Module 12: Diagnostics Statistics
Generate distributions for root cause, error type, stage, severity, impact, recommendations.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

from typing import Any, Dict, List

from diagnostic_models import EngineeringDiagnostic


class DiagnosticsStatistics:
    """Computes statistical summaries over all diagnostics."""

    def root_cause_distribution(self, diagnostics: List[EngineeringDiagnostic]) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for d in diagnostics:
            out[d.root_cause] = out.get(d.root_cause, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: kv[1], reverse=True))

    def error_type_distribution(self, diagnostics: List[EngineeringDiagnostic]) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for d in diagnostics:
            out[d.error_type] = out.get(d.error_type, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: kv[1], reverse=True))

    def pipeline_stage_distribution(self, diagnostics: List[EngineeringDiagnostic]) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for d in diagnostics:
            out[d.pipeline_stage] = out.get(d.pipeline_stage, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: kv[1], reverse=True))

    def severity_distribution(self, diagnostics: List[EngineeringDiagnostic]) -> Dict[str, int]:
        order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        out: Dict[str, int] = {s: 0 for s in order}
        for d in diagnostics:
            out[d.severity] = out.get(d.severity, 0) + 1
        return {k: v for k, v in out.items() if v > 0}

    def impact_distribution(self, diagnostics: List[EngineeringDiagnostic]) -> Dict[str, int]:
        order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        out: Dict[str, int] = {s: 0 for s in order}
        for d in diagnostics:
            out[d.impact_level] = out.get(d.impact_level, 0) + 1
        return {k: v for k, v in out.items() if v > 0}

    def recommendation_distribution(self, diagnostics: List[EngineeringDiagnostic]) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for d in diagnostics:
            key = d.root_cause
            out[key] = out.get(key, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: kv[1], reverse=True))

    def beam_diagnostic_counts(self, diagnostics: List[EngineeringDiagnostic]) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for d in diagnostics:
            if d.beam_id and d.beam_id not in ("ALL", "MULTIPLE", ""):
                for bid in d.beam_id.split(","):
                    bid = bid.strip()
                    if bid:
                        out[bid] = out.get(bid, 0) + 1
        return dict(sorted(out.items()))

    def average_confidence(self, diagnostics: List[EngineeringDiagnostic]) -> float:
        if not diagnostics:
            return 0.0
        return round(sum(d.confidence for d in diagnostics) / len(diagnostics), 4)

    def average_impact_score(self, diagnostics: List[EngineeringDiagnostic]) -> float:
        if not diagnostics:
            return 0.0
        return round(sum(d.impact_score for d in diagnostics) / len(diagnostics), 4)

    def compute_all(self, diagnostics: List[EngineeringDiagnostic]) -> Dict[str, Any]:
        return {
            "total_diagnostics": len(diagnostics),
            "root_cause_distribution": self.root_cause_distribution(diagnostics),
            "error_type_distribution": self.error_type_distribution(diagnostics),
            "pipeline_stage_distribution": self.pipeline_stage_distribution(diagnostics),
            "severity_distribution": self.severity_distribution(diagnostics),
            "impact_distribution": self.impact_distribution(diagnostics),
            "recommendation_distribution": self.recommendation_distribution(diagnostics),
            "beam_diagnostic_counts": self.beam_diagnostic_counts(diagnostics),
            "average_confidence": self.average_confidence(diagnostics),
            "average_impact_score": self.average_impact_score(diagnostics),
        }
