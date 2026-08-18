"""P2.6.3 policy. Gate runtime must stay GT-free, stratum-free, and stirrup-frozen."""
from __future__ import annotations

from .config import ENGINEERING_CHANGES, PRODUCTION_WRITE

FORBIDDEN_GATE_TOKENS = (
    "estimator_kg",
    "estimator_steel",
    "ground_truth_steel",
    "ground_truth_kg",
    "EstimatorOutput",
    "benchmark_answer",
    "expected_steel",
    "answer_workbook",
    "load_gt_universe",
    "TRUE_RECOVERY",
    "missed_gt",
    "GT_MISSING",
    "ESTIMATOR_MISMATCH",
    "BENCHMARK_FAILURE",
    "strict_true_recovery",
    "p26_compatible_true_recovery",
    "estimator_match",
    "steel_accuracy",
)

FORBIDDEN_GATE_REASONS = (
    "MISSED_GT_BAR",
    "TRUE_RECOVERY_EXPECTED",
    "GT_MISSING",
    "ESTIMATOR_MISMATCH",
    "BENCHMARK_FAILURE",
)


def assert_no_forbidden_reason(reason: str) -> None:
    if reason in FORBIDDEN_GATE_REASONS:
        raise ValueError(f"GT-derived gate reason is forbidden: {reason}")


__all__ = [
    "ENGINEERING_CHANGES",
    "FORBIDDEN_GATE_REASONS",
    "FORBIDDEN_GATE_TOKENS",
    "PRODUCTION_WRITE",
    "assert_no_forbidden_reason",
]
