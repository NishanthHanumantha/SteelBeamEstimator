"""
Stirrup Reporter — Phase SI.0 MODULE 10
Generates an engineering report covering before/after, decisions, and validation.
"""
from datetime import datetime
from typing import List, Dict, Any

from si0_stirrup_recovery_models import BeamRecoveryResult, RecoveryDecision


class StirrupRecoveryReporter:

    def __init__(
        self,
        beam_results: List[BeamRecoveryResult],
        statistics: Dict[str, Any],
        validation_passed: bool,
        validation_errors: List[str],
    ) -> None:
        self.results = beam_results
        self.stats   = statistics
        self.passed  = validation_passed
        self.errors  = validation_errors

    def build(self) -> Dict[str, Any]:
        return {
            "phase": "SI.0",
            "model_version": "6.6.2",
            "generated_at": datetime.now().isoformat(),
            "executive_summary": self._executive_summary(),
            "before_after": self._before_after(),
            "recovery_decisions": self._decisions(),
            "candidate_ranking": self._candidate_ranking(),
            "validation": {"passed": self.passed, "errors": self.errors},
            "statistics": self.stats,
        }

    def _executive_summary(self) -> Dict:
        return {
            "invalid_stirrups_corrected": self.stats.get("recovered_total", 0),
            "benchmark_beams_protected": self.stats.get("benchmark_retained", 0),
            "recovery_sources": self.stats.get("recovery_by_source", {}),
            "validation_passed": self.passed,
        }

    def _before_after(self) -> List[Dict]:
        rows = []
        for r in self.results:
            if r.original_label != r.recovered_label:
                rows.append({
                    "beam_id": r.beam_id,
                    "span_mm": r.span_mm,
                    "before": r.original_label,
                    "after": r.recovered_label,
                    "decision": r.decision.value,
                    "source": r.source.value,
                    "confidence": r.recovery_confidence,
                    "evidence": r.engineering_evidence,
                })
        return rows

    def _decisions(self) -> List[Dict]:
        return [
            {
                "beam_id": r.beam_id,
                "decision": r.decision.value,
                "source": r.source.value,
                "original_label": r.original_label,
                "recovered_label": r.recovered_label,
                "confidence": r.recovery_confidence,
                "invalid_reason": r.invalid_reason.value if r.invalid_reason else None,
                "evidence": r.engineering_evidence,
            }
            for r in self.results
        ]

    def _candidate_ranking(self) -> List[Dict]:
        return [
            {
                "beam_id": r.beam_id,
                "recovered_label": r.recovered_label,
                "source": r.source.value,
                "confidence": r.recovery_confidence,
            }
            for r in self.results
            if r.decision == RecoveryDecision.RECOVERED
        ]
