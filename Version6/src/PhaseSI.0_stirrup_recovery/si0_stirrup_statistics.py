"""
Stirrup Statistics — Phase SI.0 MODULE 9
"""
from typing import List, Dict, Any
from si0_stirrup_recovery_models import BeamRecoveryResult, RecoveryDecision, RecoverySource


def compute_statistics(
    beam_results: List[BeamRecoveryResult],
    total_beams: int,
) -> Dict[str, Any]:
    retained   = [r for r in beam_results if r.decision == RecoveryDecision.RETAINED]
    recovered  = [r for r in beam_results if r.decision == RecoveryDecision.RECOVERED]
    failed     = [r for r in beam_results if r.decision == RecoveryDecision.FAILED]

    src_counts: Dict[str, int] = {}
    for r in recovered:
        src_counts[r.source.value] = src_counts.get(r.source.value, 0) + 1

    return {
        "total_beams": total_beams,
        "beams_with_stirrup_entries": len(beam_results),
        "benchmark_retained": sum(
            1 for r in retained if r.source == RecoverySource.BENCHMARK
        ),
        "valid_retained": sum(
            1 for r in retained if r.source not in (RecoverySource.BENCHMARK, RecoverySource.NO_STIRRUP)
        ),
        "no_stirrup_beams": sum(
            1 for r in retained if r.source == RecoverySource.NO_STIRRUP
        ),
        "invalid_stirrups_found": sum(1 for r in beam_results if r.invalid_reason is not None),
        "recovered_total": len(recovered),
        "recovery_by_source": src_counts,
        "failed_recovery": len(failed),
        "recovery_success_rate_percent": round(
            100 * len(recovered) / max(1, sum(1 for r in beam_results if r.invalid_reason))
            if any(r.invalid_reason for r in beam_results) else 100.0, 1
        ),
    }
