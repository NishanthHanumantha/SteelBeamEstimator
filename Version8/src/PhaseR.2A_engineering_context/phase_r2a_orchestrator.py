"""
Phase R.2A Orchestrator.

Runs the complete engineering context pipeline:
  1. Discover GN DXF
  2. Parse all engineering parameters
  3. Build EngineeringContext
  4. Validate
  5. Run audit (17 criteria)
  6. Export JSON artefacts

MODEL_VERSION: 7.5.4
"""
from __future__ import annotations
import pathlib
from datetime import datetime
from typing import Any, Dict, List

from .engineering_context_factory    import EngineeringContextFactory
from .engineering_context_builder    import EngineeringContextBuilder
from .engineering_context_loader     import EngineeringContextLoader
from .engineering_context_validator  import EngineeringContextValidator
from .engineering_context_audit      import EngineeringContextAudit
from .engineering_context_statistics import EngineeringContextStatistics
from .engineering_context_writer     import EngineeringContextWriter
from .engineering_context_validation import EngineeringContextValidation
from .engineering_context_model      import EngineeringContext


class PhaseR2AOrchestrator:

    def __init__(self, v7_root: pathlib.Path, output_dir: pathlib.Path):
        self._v7  = v7_root
        self._out = output_dir

    def run(self) -> Dict[str, Any]:
        print(f"\n{'='*70}")
        print("  PHASE R.2A / R.2A.1 — Engineering Context Parsing")
        print(f"  MODEL_VERSION 7.5.4  |  {datetime.utcnow().isoformat()}")
        print(f"  Block-expanded extraction | 10-rule validation")
        print(f"{'='*70}\n")

        # ------------------------------------------------------------------
        # Step 1: Discover + build (force rebuild for fresh dl_audit)
        # ------------------------------------------------------------------
        print("[1/5] Discovering GN DXF and building EngineeringContext ...")
        gn_path = EngineeringContextFactory._discover_gn_path(self._v7)
        if gn_path is None:
            print("  ERROR: GN DXF not found — cannot build EngineeringContext.")
            return {"status": "FAIL", "reason": "GN DXF not found"}

        project_id = EngineeringContextFactory._read_project_id(self._v7)
        builder = EngineeringContextBuilder(gn_path, project_id)
        ctx = builder.build()
        dl_audit = builder.dl_audit

        validator = EngineeringContextValidator()
        validation_passed, val_warnings = validator.validate(ctx)
        loader = EngineeringContextLoader(ctx)
        print(f"     GN DXF:          {ctx.gn_dxf_path}")
        print(f"     Parse confidence:{ctx.parse_confidence:.1%}")
        print(f"     Steel grade:     {ctx.primary_steel_grade}")
        print(f"     Concrete grades: {list(ctx.concrete_grades)}")
        print(f"     DL table entries:{len(ctx.development_length_table)}")
        print(f"     Cover rules:     {len(ctx.cover_rules)}")

        # ------------------------------------------------------------------
        # Step 2: Loader summary
        # ------------------------------------------------------------------
        print("\n[2/5] Engineering Context Loader Summary ...")
        summary = loader.summary()
        for k, v in summary.items():
            if k != "fallback_log":
                print(f"     {k}: {v}")

        # ------------------------------------------------------------------
        # Step 3: Run 17-criteria audit
        # ------------------------------------------------------------------
        print("\n[3/5] Running 17-criteria audit ...")
        auditor = EngineeringContextAudit()
        audit_results = auditor.audit(ctx, loader, validation_passed)
        passed_count = sum(1 for r in audit_results if r.passed)
        total_count  = len(audit_results)

        for r in audit_results:
            status = "PASS" if r.passed else "FAIL"
            print(f"     [{status}] {r.criterion}")
            if r.evidence:
                print(f"           {r.evidence[:80]}")

        # ------------------------------------------------------------------
        # Step 4: Statistics
        # ------------------------------------------------------------------
        print(f"\n[4/5] Computing statistics ...")
        stats = EngineeringContextStatistics(ctx).compute()
        dl_sg = stats["dev_length_table"]["steel_grades_in_table"]
        dl_dia = stats["dev_length_table"]["diameters_mm"]
        print(f"     DL steel grades in table: {dl_sg}")
        print(f"     DL diameters covered: {dl_dia}")
        print(f"     Cover elements: {stats['cover_rules']['elements']}")

        # ------------------------------------------------------------------
        # Step 5: Export
        # ------------------------------------------------------------------
        # ------------------------------------------------------------------
        # Step 3b: Run 10-rule Fe550 validation
        # ------------------------------------------------------------------
        print("\n[3b] Running 10-rule Fe550 validation ...")
        fe550_validator = EngineeringContextValidation()
        fe550_results   = fe550_validator.run(ctx, loader, dl_audit)
        fe550_passed    = sum(1 for r in fe550_results if r.passed)
        for r in fe550_results:
            st = "PASS" if r.passed else "FAIL"
            print(f"     [{st}] {r.rule_id}: {r.description}")

        print(f"\n[5/5] Exporting 7 JSON artefacts to: {self._out}")
        writer = EngineeringContextWriter(self._out)
        paths = writer.write_all(ctx, loader, validation_passed, val_warnings, dl_audit)
        for name, path in paths.items():
            print(f"     {name}: {path}")

        # ------------------------------------------------------------------
        # Final summary
        # ------------------------------------------------------------------
        self._print_final(audit_results, passed_count, total_count, ctx, loader,
                          fe550_passed, len(fe550_results), dl_audit)

        overall_pass = (passed_count == total_count and fe550_passed == len(fe550_results))
        return {
            "status": "PASS" if overall_pass else "PARTIAL",
            "audit_score": f"{passed_count}/{total_count}",
            "fe550_validation_score": f"{fe550_passed}/{len(fe550_results)}",
            "validation_passed": validation_passed,
            "primary_steel_grade": ctx.primary_steel_grade,
            "cover_beam_mm": loader.get_cover("BEAM"),
            "dl_table_entries": len(ctx.development_length_table),
            "parse_confidence": ctx.parse_confidence,
            "export_paths": paths,
        }

    def _extract_dl_audit(self, ctx: EngineeringContext) -> Dict[str, Any]:
        """Reconstruct dl_audit from context when builder audit is unavailable."""
        dxf_grades = set()
        for key in ctx.development_length_table:
            dxf_grades.add(key[0])
        fe550_in_dxf = "Fe550" in dxf_grades
        return {
            "dxf_table_headers_found": [f"LD FOR FY-{g[2:]}" for g in sorted(dxf_grades)],
            "tables_parsed_from_dxf": [f"{g}: parsed" for g in sorted(dxf_grades)],
            "tables_computed_is456": [],
            "fe550_in_dxf": fe550_in_dxf,
            "fe550_computed": False,
            "root_cause": (
                "All development-length tables extracted from GN DXF."
                if fe550_in_dxf else
                "FY-550 table not found; IS456 fallback may apply."
            ),
        }

    def _print_final(self, audit_results, passed, total, ctx, loader,
                     fe550_passed=None, fe550_total=None, dl_audit=None):
        print(f"\n{'='*70}")
        print(f"  PHASE R.2A.1 COMPLETE")
        print(f"{'='*70}")
        print(f"  17-criteria audit: {passed}/{total}")
        if fe550_passed is not None:
            print(f"  10-rule Fe550 val: {fe550_passed}/{fe550_total}")
        print(f"  Parse confidence:  {ctx.parse_confidence:.1%}")
        print(f"\n  ENGINEERING CONTEXT:")
        print(f"    Primary steel grade  : {ctx.primary_steel_grade}")
        print(f"    All steel grades     : {list(ctx.steel_grades)}")
        fe550_cnt = sum(1 for k in ctx.development_length_table if k[0]=="Fe550")
        fe415_cnt = sum(1 for k in ctx.development_length_table if k[0]=="Fe415")
        fe500_cnt = sum(1 for k in ctx.development_length_table if k[0]=="Fe500")
        print(f"    DL table Fe415       : {fe415_cnt} entries (GN_DXF_TABLE_1)")
        print(f"    DL table Fe500       : {fe500_cnt} entries (GN_DXF_TABLE_1)")
        fe550_source = "GN_DXF_TABLE_1" if dl_audit and dl_audit.get("fe550_in_dxf") else "IS456_2000_COMPUTED"
        print(f"    DL table Fe550       : {fe550_cnt} entries ({fe550_source})")
        print(f"    Beam cover           : {loader.get_cover('BEAM')}mm")
        ld12 = loader.get_development_length_mm(12, "M30", "Fe550")
        ld16 = loader.get_development_length_mm(16, "M30", "Fe550")
        ld20 = loader.get_development_length_mm(20, "M30", "Fe550")
        print(f"\n  Fe550 LOOKUP ({fe550_source}):")
        print(f"    Ld dia=12, M30, Fe550: {ld12}mm")
        print(f"    Ld dia=16, M30, Fe550: {ld16}mm")
        print(f"    Ld dia=20, M30, Fe550: {ld20}mm")
        print(f"    Factor dia12         : {round(ld12/12)}d")
        print(f"\n  PIPELINE IMPACT vs. HARDCODED CONSTANTS:")
        print(f"    Cover  : pipeline=40mm -> GN={loader.get_cover('BEAM')}mm")
        pi_dl  = 40 * 12
        print(f"    Ld dia12 M30: pipeline={pi_dl}mm -> Fe550={ld12}mm")
        print(f"    Steel  : pipeline=Fe415 -> GN={ctx.primary_steel_grade}")
        print(f"{'='*70}\n")
