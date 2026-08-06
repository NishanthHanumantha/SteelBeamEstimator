"""
Confidence scoring for EngineeringIssue (0–1).
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

from typing import List

from engineering_issue_model import RawFinding

MODEL_VERSION = "8.7.0"


class ConfidenceEngine:
    def score(
        self,
        findings: List[RawFinding],
        phase_certainty: float,
        category_consistency: float,
    ) -> float:
        freq = len(findings)
        freq_score = min(1.0, 0.35 + 0.05 * freq)  # more occurrences → higher confidence
        evidence = min(1.0, freq / 10.0)
        confs = [f.confidence for f in findings if f.confidence > 0]
        agreement = sum(confs) / len(confs) if confs else 0.5
        # phase certainty from attribution vote dominance (0–1)
        score = (
            0.25 * freq_score
            + 0.20 * evidence
            + 0.25 * agreement
            + 0.15 * phase_certainty
            + 0.15 * category_consistency
        )
        return round(max(0.0, min(1.0, score)), 4)
