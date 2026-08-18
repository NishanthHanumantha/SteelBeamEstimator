"""P2.6.3 coverage evaluator re-export. P2.6.4 does not rewrite it."""
from PhaseP263_longitudinal_aware_gate.longitudinal_coverage import (
    evaluate_longitudinal_coverage,
    parse_longitudinal_annotation,
)

__all__ = ["evaluate_longitudinal_coverage", "parse_longitudinal_annotation"]
