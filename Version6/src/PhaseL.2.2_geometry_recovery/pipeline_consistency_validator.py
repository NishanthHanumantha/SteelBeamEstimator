"""
Pipeline Consistency Validator — fail-fast rule engine.

Rule 1: Feature Beam Count == Geometry Beam Count
Rule 2: Geometry Beam Count == Specification Beam Count
Rule 3: Specification Beam Count == Engineering Object Count
Rule 4: Engineering Object Count == Detected Beam Count

Any violated rule raises PIPELINE_COVERAGE_ERROR.
All rules are evaluated even when strict_mode=False so the caller receives
a full diagnostic payload regardless.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class PipelineCoverageError(Exception):
    """Raised when pipeline beam counts are inconsistent across stages."""


@dataclass
class ConsistencyRule:
    rule_id: str
    description: str
    expected_count: int
    actual_count: int
    passed: bool = field(init=False)

    def __post_init__(self) -> None:
        self.passed = self.expected_count == self.actual_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "expected_count": self.expected_count,
            "actual_count": self.actual_count,
            "passed": self.passed,
        }


class PipelineConsistencyValidator:
    """
    Validates that beam counts are equal across every pipeline stage.

    Parameters
    ----------
    strict_mode:
        When True (default) a PIPELINE_COVERAGE_ERROR is raised on any failure.
        When False violations are reported but execution continues.
    """

    def __init__(self, strict_mode: bool = True) -> None:
        self._strict = strict_mode

    def validate(
        self,
        detected_beam_count: int,
        engineering_object_count: int,
        specification_count: int,
        geometry_count: int,
        feature_beam_count: int,
    ) -> Dict[str, Any]:
        """
        Run all four consistency rules.

        Returns
        -------
        Dict with pipeline_status (PASS | FAIL), rules list, and counts.

        Raises
        ------
        PipelineCoverageError — when strict_mode=True and any rule fails.
        """
        rules: List[ConsistencyRule] = [
            ConsistencyRule(
                rule_id="RULE_1",
                description="Feature Beam Count == Geometry Beam Count",
                expected_count=geometry_count,
                actual_count=feature_beam_count,
            ),
            ConsistencyRule(
                rule_id="RULE_2",
                description="Geometry Beam Count == Specification Beam Count",
                expected_count=specification_count,
                actual_count=geometry_count,
            ),
            ConsistencyRule(
                rule_id="RULE_3",
                description="Specification Beam Count == Engineering Object Count",
                expected_count=engineering_object_count,
                actual_count=specification_count,
            ),
            ConsistencyRule(
                rule_id="RULE_4",
                description="Engineering Object Count == Detected Beam Count",
                expected_count=detected_beam_count,
                actual_count=engineering_object_count,
            ),
        ]

        all_pass = all(r.passed for r in rules)
        pipeline_status = "PASS" if all_pass else "FAIL"

        failed_rules = [r for r in rules if not r.passed]
        if not all_pass and self._strict:
            detail = "; ".join(
                f"{r.rule_id} ({r.description}): expected={r.expected_count} actual={r.actual_count}"
                for r in failed_rules
            )
            raise PipelineCoverageError(
                f"PIPELINE_COVERAGE_ERROR: {len(failed_rules)} rule(s) failed — {detail}"
            )

        return {
            "pipeline_status": pipeline_status,
            "all_rules_passed": all_pass,
            "counts": {
                "detected_beams": detected_beam_count,
                "engineering_objects": engineering_object_count,
                "specifications": specification_count,
                "geometry_objects": geometry_count,
                "feature_beams": feature_beam_count,
            },
            "rules": [r.to_dict() for r in rules],
            "failed_rules": [r.to_dict() for r in failed_rules],
        }
