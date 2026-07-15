"""
Engineering Context Validation — 10 rules for Phase R.2A.1

Validates that the Fe550 development length table is properly populated
(either from GN DXF directly, or from IS 456:2000 formula computation),
and that the loader correctly resolves Fe550 without silent substitution.
"""
from __future__ import annotations
from typing import Any, Dict, List

from .engineering_context_model  import EngineeringContext
from .engineering_context_loader import EngineeringContextLoader

_EXPECTED_DIAMETERS    = {8, 10, 12, 16, 20, 25, 32}
_EXPECTED_CONC_GRADES  = {"M20", "M25", "M30", "M35", "M40"}
_MIN_EXPECTED_ENTRIES  = len(_EXPECTED_DIAMETERS) * len(_EXPECTED_CONC_GRADES)  # 35


class ValidationResult:
    def __init__(self, rule_id: str, description: str, passed: bool,
                 evidence: str, detail: str = ""):
        self.rule_id     = rule_id
        self.description = description
        self.passed      = passed
        self.evidence    = evidence
        self.detail      = detail

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id":     self.rule_id,
            "description": self.description,
            "passed":      self.passed,
            "status":      "PASS" if self.passed else "FAIL",
            "evidence":    self.evidence,
            "detail":      self.detail,
        }


class EngineeringContextValidation:
    """10-rule validation suite for Phase R.2A.1."""

    def run(
        self,
        ctx: EngineeringContext,
        loader: EngineeringContextLoader,
        dl_audit: Dict[str, Any],
    ) -> List[ValidationResult]:
        return [
            self._rule1_fe550_table_exists(ctx),
            self._rule2_fe550_row_count(ctx),
            self._rule3_fe550_column_count(ctx),
            self._rule4_all_diameters_parsed(ctx),
            self._rule5_all_conc_grades_parsed(ctx),
            self._rule6_no_empty_lookup_values(ctx),
            self._rule7_loader_returns_fe550(ctx, loader),
            self._rule8_no_fe415_fallback(ctx, loader),
            self._rule9_engineering_context_updated(ctx),
            self._rule10_no_regression(ctx),
        ]

    def _fe550_keys(self, ctx: EngineeringContext) -> Dict:
        return {
            k: v for k, v in ctx.development_length_table.items()
            if k[0] == "Fe550"
        }

    def _rule1_fe550_table_exists(self, ctx: EngineeringContext) -> ValidationResult:
        fe550 = self._fe550_keys(ctx)
        passed = len(fe550) > 0
        return ValidationResult(
            "RULE_1",
            "Fe550 table discovered (DXF or IS456 computed)",
            passed,
            f"Fe550 entries in table: {len(fe550)}",
            "Source may be IS456_2000_COMPUTED if not in GN DXF",
        )

    def _rule2_fe550_row_count(self, ctx: EngineeringContext) -> ValidationResult:
        fe550 = self._fe550_keys(ctx)
        fe415 = {k: v for k, v in ctx.development_length_table.items() if k[0] == "Fe415"}
        expected = len(set(k[1] for k in fe415)) if fe415 else len(_EXPECTED_DIAMETERS)
        actual   = len(set(k[1] for k in fe550))
        passed   = actual >= expected
        return ValidationResult(
            "RULE_2",
            "Fe550 row count correct (same diameters as Fe415)",
            passed,
            f"Expected diameters: {expected}, Fe550 diameters: {actual}",
            str(sorted({k[1] for k in fe550})),
        )

    def _rule3_fe550_column_count(self, ctx: EngineeringContext) -> ValidationResult:
        fe550 = self._fe550_keys(ctx)
        fe415 = {k: v for k, v in ctx.development_length_table.items() if k[0] == "Fe415"}
        expected = len(set(k[2] for k in fe415)) if fe415 else len(_EXPECTED_CONC_GRADES)
        actual   = len(set(k[2] for k in fe550))
        passed   = actual >= expected
        return ValidationResult(
            "RULE_3",
            "Fe550 column count correct (same concrete grades as Fe415)",
            passed,
            f"Expected concrete grades: {expected}, Fe550 grades: {actual}",
            str(sorted({k[2] for k in fe550})),
        )

    def _rule4_all_diameters_parsed(self, ctx: EngineeringContext) -> ValidationResult:
        fe550 = self._fe550_keys(ctx)
        found   = {k[1] for k in fe550}
        expected = _EXPECTED_DIAMETERS
        missing  = expected - found
        passed   = len(missing) == 0
        return ValidationResult(
            "RULE_4",
            "All standard diameters parsed for Fe550",
            passed,
            f"Found: {sorted(found)} | Missing: {sorted(missing)}",
        )

    def _rule5_all_conc_grades_parsed(self, ctx: EngineeringContext) -> ValidationResult:
        fe550 = self._fe550_keys(ctx)
        found   = {k[2] for k in fe550}
        expected = _EXPECTED_CONC_GRADES
        missing  = expected - found
        passed   = len(missing) == 0
        return ValidationResult(
            "RULE_5",
            "All standard concrete grades parsed for Fe550",
            passed,
            f"Found: {sorted(found)} | Missing: {sorted(missing)}",
        )

    def _rule6_no_empty_lookup_values(self, ctx: EngineeringContext) -> ValidationResult:
        fe550 = self._fe550_keys(ctx)
        empty = [k for k, v in fe550.items() if not v or v <= 0]
        passed = len(empty) == 0
        return ValidationResult(
            "RULE_6",
            "No empty/zero lookup values for Fe550",
            passed,
            f"Invalid entries: {len(empty)} | Total Fe550: {len(fe550)}",
        )

    def _rule7_loader_returns_fe550(
        self, ctx: EngineeringContext, loader: EngineeringContextLoader
    ) -> ValidationResult:
        fe550_keys = self._fe550_keys(ctx)
        if not fe550_keys:
            return ValidationResult(
                "RULE_7", "Loader returns Fe550 values", False,
                "No Fe550 entries in table", ""
            )
        # Pick a specific key and verify loader returns exact value
        sample_key = next(iter(fe550_keys))
        dia_mm = sample_key[1]
        cg     = sample_key[2]
        expected_val = ctx.development_length_table[sample_key]
        # Create fresh loader to avoid side effects from previous calls
        from .engineering_context_loader import EngineeringContextLoader
        fresh = EngineeringContextLoader(ctx)
        actual_val = fresh.get_development_length_mm(dia_mm, cg, "Fe550")
        passed = (actual_val == expected_val)
        return ValidationResult(
            "RULE_7",
            "Loader returns Fe550 values when steel_grade=Fe550 requested",
            passed,
            f"dia={dia_mm}, cg={cg}: expected={expected_val}mm, got={actual_val}mm",
        )

    def _rule8_no_fe415_fallback(
        self, ctx: EngineeringContext, loader: EngineeringContextLoader
    ) -> ValidationResult:
        """Verify that fetching Fe550 does NOT produce a Fe415 substitution warning."""
        from .engineering_context_loader import EngineeringContextLoader
        fresh = EngineeringContextLoader(ctx)
        _ = fresh.get_development_length_mm(12, "M30", "Fe550")
        fe415_substitutions = [
            log for log in fresh.fallback_log
            if "Fe415" in log and "instead of Fe550" in log
        ]
        passed = len(fe415_substitutions) == 0
        return ValidationResult(
            "RULE_8",
            "No Fe415 substitution when Fe550 requested",
            passed,
            f"Fe415-substitution events: {len(fe415_substitutions)}",
            str(fe415_substitutions[:3]),
        )

    def _rule9_engineering_context_updated(self, ctx: EngineeringContext) -> ValidationResult:
        fe550_in_grades = "Fe550" in ctx.steel_grades
        fe550_in_table  = any(k[0] == "Fe550" for k in ctx.development_length_table)
        passed = fe550_in_grades and fe550_in_table
        return ValidationResult(
            "RULE_9",
            "Engineering context updated: Fe550 in steel_grades and dev_table",
            passed,
            f"Fe550 in steel_grades: {fe550_in_grades} | in dev_table: {fe550_in_table}",
            f"All steel grades: {list(ctx.steel_grades)}",
        )

    def _rule10_no_regression(self, ctx: EngineeringContext) -> ValidationResult:
        """Fe415 and Fe500 tables must still be fully present."""
        fe415_count = sum(1 for k in ctx.development_length_table if k[0] == "Fe415")
        fe500_count = sum(1 for k in ctx.development_length_table if k[0] == "Fe500")
        passed = fe415_count >= 30 and fe500_count >= 30
        return ValidationResult(
            "RULE_10",
            "No regression: Fe415 and Fe500 tables still fully present",
            passed,
            f"Fe415: {fe415_count} entries | Fe500: {fe500_count} entries",
            f"Expected >=30 each (6 diameters x 5 grades)",
        )
