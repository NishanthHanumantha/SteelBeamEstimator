"""
Pattern Validator.

Rules
-----
RULE_1  Pattern Count == Feature Beam Count
RULE_2  Pattern Count == Geometry Count
RULE_3  Pattern Count == Engineering Object Count
RULE_4  No duplicate beam IDs

Raises PatternValidationError when strict_mode=True and any rule fails.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from pattern_models import EngineeringPattern
from pattern_registry import PatternRegistry


class PatternValidationError(Exception):
    """Raised when pattern validation fails in strict mode."""


@dataclass
class ValidationRule:
    rule_id: str
    description: str
    expected: int
    actual: int
    passed: bool = field(init=False)

    def __post_init__(self) -> None:
        self.passed = self.expected == self.actual

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "expected": self.expected,
            "actual": self.actual,
            "passed": self.passed,
        }


class PatternValidator:

    def __init__(self, strict_mode: bool = True) -> None:
        self._strict = strict_mode

    def validate_collection(
        self,
        registry: PatternRegistry,
        feature_beam_count: int,
        geometry_count: int,
        engineering_object_count: int,
    ) -> Dict[str, Any]:
        pattern_count = registry.count()
        beam_ids = registry.beam_ids()

        # Rule 4: no duplicate beam IDs
        seen: Set[str] = set()
        duplicates: List[str] = []
        for bid in beam_ids:
            if bid in seen:
                duplicates.append(bid)
            seen.add(bid)
        no_duplicates = len(duplicates) == 0

        rules = [
            ValidationRule(
                "RULE_1",
                "Pattern Count == Feature Beam Count",
                feature_beam_count,
                pattern_count,
            ),
            ValidationRule(
                "RULE_2",
                "Pattern Count == Geometry Count",
                geometry_count,
                pattern_count,
            ),
            ValidationRule(
                "RULE_3",
                "Pattern Count == Engineering Object Count",
                engineering_object_count,
                pattern_count,
            ),
        ]
        duplicate_rule = {
            "rule_id": "RULE_4",
            "description": "No duplicate beam IDs",
            "duplicates_found": duplicates,
            "passed": no_duplicates,
        }

        all_pass = all(r.passed for r in rules) and no_duplicates
        failed = [r.to_dict() for r in rules if not r.passed]
        if not no_duplicates:
            failed.append(duplicate_rule)

        # Update registry validation status
        for bid in beam_ids:
            registry.update_validation_status(bid, "PASS" if all_pass else "FAIL")

        if not all_pass and self._strict:
            detail = "; ".join(
                f"{r['rule_id']} expected={r.get('expected')} actual={r.get('actual')}"
                if "expected" in r else f"{r['rule_id']} duplicates={r.get('duplicates_found')}"
                for r in failed
            )
            raise PatternValidationError(
                f"PATTERN_VALIDATION_ERROR: {len(failed)} rule(s) failed — {detail}"
            )

        return {
            "status": "PASS" if all_pass else "FAIL",
            "all_rules_passed": all_pass,
            "pattern_count": pattern_count,
            "feature_beam_count": feature_beam_count,
            "geometry_count": geometry_count,
            "engineering_object_count": engineering_object_count,
            "rules": [r.to_dict() for r in rules] + [duplicate_rule],
            "failed_rules": failed,
        }

    def validate_single(self, pattern: EngineeringPattern) -> Dict[str, Any]:
        issues: List[str] = []
        if not pattern.beam_id:
            issues.append("Missing beam_id")
        if not pattern.span_pattern:
            issues.append("Missing span_pattern")
        if not pattern.continuity_pattern:
            issues.append("Missing continuity_pattern")
        if not (0.0 <= pattern.classification_confidence <= 1.0):
            issues.append("Confidence out of range")
        return {"beam_id": pattern.beam_id, "passed": len(issues) == 0, "issues": issues}
