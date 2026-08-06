"""
Engineering Context Regression Validator — 10 rules for Phase R.2A.3
MODEL_VERSION: 7.5.4
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Set, Tuple

from .engineering_context_audit import ContextAuditResult, EngineeringContextAudit
from .engineering_context_loader import EngineeringContextLoader
from .engineering_context_model import EngineeringContext
from .general_notes_text_extractor import GeneralNotesTextExtractor

_EXPECTED_STEEL_GRADES = ("Fe415", "Fe500", "Fe550")
_EXPECTED_DIAMETERS = {8, 10, 12, 16, 20, 25, 32}
_EXPECTED_CONC_GRADES = {"M20", "M25", "M30", "M35", "M40"}
_ENTRIES_PER_GRADE = 35
_TOTAL_DL_ENTRIES = 105


class RegressionValidationResult:
    def __init__(self, rule_id: str, description: str, passed: bool,
                 evidence: str, detail: str = ""):
        self.rule_id = rule_id
        self.description = description
        self.passed = passed
        self.evidence = evidence
        self.detail = detail

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "passed": self.passed,
            "status": "PASS" if self.passed else "FAIL",
            "evidence": self.evidence,
            "detail": self.detail,
        }


class EngineeringContextRegressionValidator:
    """10-rule regression validation suite for Phase R.2A.3."""

    def validate(
        self,
        ctx: EngineeringContext,
        loader: EngineeringContextLoader,
        dl_audit: Dict[str, Any],
        extractor: GeneralNotesTextExtractor,
        validation_passed: bool,
        audit_results: Optional[List[ContextAuditResult]] = None,
    ) -> List[RegressionValidationResult]:
        audit_results = audit_results or []
        expansion = extractor.get_expansion_report()
        return [
            self._rule1_context_regenerated(ctx, expansion),
            self._rule2_fe415_complete(ctx),
            self._rule3_fe500_complete(ctx),
            self._rule4_fe550_complete(ctx),
            self._rule5_total_dl_entries(ctx),
            self._rule6_zero_fallback_events(ctx, loader, dl_audit),
            self._rule7_zero_computed_dl(dl_audit),
            self._rule8_parameters_sourced(ctx, dl_audit),
            self._rule9_backward_compatible(ctx, loader),
            self._rule10_audit_passes(validation_passed, audit_results),
        ]

    def _grade_keys(self, ctx: EngineeringContext, grade: str) -> Dict:
        return {k: v for k, v in ctx.development_length_table.items() if k[0] == grade}

    def _grade_complete(self, ctx: EngineeringContext, grade: str) -> Tuple[bool, str]:
        keys = self._grade_keys(ctx, grade)
        diameters = {k[1] for k in keys}
        conc = {k[2] for k in keys}
        missing_dia = _EXPECTED_DIAMETERS - diameters
        missing_conc = _EXPECTED_CONC_GRADES - conc
        passed = (
            len(keys) == _ENTRIES_PER_GRADE
            and not missing_dia
            and not missing_conc
        )
        evidence = (
            f"{grade}: {len(keys)} entries | "
            f"diameters={sorted(diameters)} | grades={sorted(conc)}"
        )
        detail = ""
        if missing_dia:
            detail += f"missing diameters: {sorted(missing_dia)}; "
        if missing_conc:
            detail += f"missing concrete grades: {sorted(missing_conc)}"
        return passed, evidence + (f" | {detail}" if detail else "")

    def _rule1_context_regenerated(
        self, ctx: EngineeringContext, expansion: Dict[str, Any]
    ) -> RegressionValidationResult:
        passed = bool(ctx.gn_dxf_path) and bool(ctx.parsed_at) and len(ctx.development_length_table) > 0
        return RegressionValidationResult(
            "RULE_1",
            "Engineering Context regenerated",
            passed,
            f"GN DXF: {ctx.gn_dxf_path} | Parsed: {ctx.parsed_at} | "
            f"INSERT expanded: {expansion.get('insert_blocks_expanded', 0)}",
        )

    def _rule2_fe415_complete(self, ctx: EngineeringContext) -> RegressionValidationResult:
        passed, evidence = self._grade_complete(ctx, "Fe415")
        return RegressionValidationResult("RULE_2", "Fe415 table complete", passed, evidence)

    def _rule3_fe500_complete(self, ctx: EngineeringContext) -> RegressionValidationResult:
        passed, evidence = self._grade_complete(ctx, "Fe500")
        return RegressionValidationResult("RULE_3", "Fe500 table complete", passed, evidence)

    def _rule4_fe550_complete(self, ctx: EngineeringContext) -> RegressionValidationResult:
        passed, evidence = self._grade_complete(ctx, "Fe550")
        return RegressionValidationResult("RULE_4", "Fe550 table complete", passed, evidence)

    def _rule5_total_dl_entries(self, ctx: EngineeringContext) -> RegressionValidationResult:
        total = len(ctx.development_length_table)
        by_grade = {g: sum(1 for k in ctx.development_length_table if k[0] == g)
                    for g in _EXPECTED_STEEL_GRADES}
        passed = total == _TOTAL_DL_ENTRIES
        return RegressionValidationResult(
            "RULE_5",
            "105 Development Length entries available",
            passed,
            f"Total: {total} | By grade: {by_grade}",
        )

    def _rule6_zero_fallback_events(
        self,
        ctx: EngineeringContext,
        loader: EngineeringContextLoader,
        dl_audit: Dict[str, Any],
    ) -> RegressionValidationResult:
        fresh = EngineeringContextLoader(ctx)
        _ = fresh.get_development_length_mm(12, "M30", "Fe550")
        _ = fresh.get_cover("BEAM")
        _ = fresh.get_primary_steel_grade()
        build_fallbacks = [
            w for w in ctx.warnings
            if "IS456" in w.upper() or "not in GN DXF" in w
        ]
        loader_events = len(fresh.fallback_log)
        is456_computed = dl_audit.get("tables_computed_is456", [])
        passed = (
            loader_events == 0
            and len(build_fallbacks) == 0
            and len(is456_computed) == 0
        )
        return RegressionValidationResult(
            "RULE_6",
            "Zero fallback events",
            passed,
            f"Loader fallbacks: {loader_events} | Build warnings: {len(build_fallbacks)} | "
            f"IS456 computed tables: {len(is456_computed)}",
        )

    def _rule7_zero_computed_dl(self, dl_audit: Dict[str, Any]) -> RegressionValidationResult:
        computed = dl_audit.get("tables_computed_is456", [])
        fe550_computed = dl_audit.get("fe550_computed", False)
        passed = len(computed) == 0 and not fe550_computed
        return RegressionValidationResult(
            "RULE_7",
            "Zero computed Development Length values",
            passed,
            f"tables_computed_is456: {computed} | fe550_computed: {fe550_computed}",
        )

    def _rule8_parameters_sourced(
        self, ctx: EngineeringContext, dl_audit: Dict[str, Any]
    ) -> RegressionValidationResult:
        checks: List[str] = []
        passed = True

        if not ctx.primary_steel_grade:
            passed = False
            checks.append("steel_grade: MISSING")
        else:
            checks.append(f"steel_grade: DXF ({ctx.primary_steel_grade})")

        if not ctx.concrete_grades:
            passed = False
            checks.append("concrete_grade: MISSING")
        else:
            checks.append(f"concrete_grade: DXF ({list(ctx.concrete_grades)})")

        if dl_audit.get("fe550_in_dxf") and len(dl_audit.get("tables_computed_is456", [])) == 0:
            checks.append("development_length: DXF (all 3 grades)")
        else:
            passed = False
            checks.append("development_length: NOT fully DXF")

        cover_from_dxf = all(
            "FALLBACK" not in r.source.upper() for r in ctx.cover_rules
        ) if ctx.cover_rules else False
        if cover_from_dxf:
            checks.append(f"cover: DXF ({len(ctx.cover_rules)} rules)")
        else:
            passed = False
            checks.append("cover: FALLBACK detected")

        hook_from_dxf = all(
            "FALLBACK" not in r.source.upper() for r in ctx.hook_rules
        ) if ctx.hook_rules else False
        if hook_from_dxf:
            checks.append(f"hook_rules: DXF ({len(ctx.hook_rules)} rules)")
        else:
            passed = False
            checks.append("hook_rules: FALLBACK detected")

        lap_from_dxf = all(
            "FALLBACK" not in r.source.upper() for r in ctx.lap_rules
        ) if ctx.lap_rules else False
        if lap_from_dxf:
            checks.append(f"lap_rules: DXF ({len(ctx.lap_rules)} rules)")
        else:
            passed = False
            checks.append("lap_rules: FALLBACK detected")

        checks.append(f"spacer_rules: DXF ({len(ctx.spacer_rules)} rules)")
        checks.append(f"code_references: DXF ({len(ctx.code_references)} refs)")

        return RegressionValidationResult(
            "RULE_8",
            "All engineering parameters sourced correctly",
            passed,
            "; ".join(checks),
        )

    def _rule9_backward_compatible(
        self, ctx: EngineeringContext, loader: EngineeringContextLoader
    ) -> RegressionValidationResult:
        try:
            d = ctx.to_dict()
            required_keys: Set[str] = {
                "primary_steel_grade", "concrete_grades", "development_length_table",
                "cover_rules", "hook_rules", "lap_rules", "fallback_cover_mm",
            }
            schema_ok = required_keys.issubset(d.keys())
            api_ok = all(
                v is not None for v in [
                    loader.get_cover("BEAM"),
                    loader.get_primary_steel_grade(),
                    loader.get_concrete_grade("BEAM"),
                    loader.get_development_length_factor(),
                    loader.get_hook_multiple(135),
                    loader.get_minimum_lap_mm(),
                ]
            )
            passed = schema_ok and api_ok
            evidence = (
                f"Schema keys: {len(d)} | Required present: {schema_ok} | "
                f"Loader API accessible: {api_ok}"
            )
        except Exception as exc:
            passed = False
            evidence = f"Backward compatibility check failed: {exc}"
        return RegressionValidationResult(
            "RULE_9",
            "Backward compatibility maintained",
            passed,
            evidence,
        )

    def _rule10_audit_passes(
        self,
        validation_passed: bool,
        audit_results: List[ContextAuditResult],
    ) -> RegressionValidationResult:
        passed_count = sum(1 for r in audit_results if r.passed)
        total = len(audit_results)
        passed = validation_passed and passed_count == total and total == 17
        return RegressionValidationResult(
            "RULE_10",
            "17/17 Engineering Context audit passes",
            passed,
            f"Build validation: {validation_passed} | Audit: {passed_count}/{total}",
        )
