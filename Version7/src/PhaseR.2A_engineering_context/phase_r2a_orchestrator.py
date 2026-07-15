"""
Phase R.2A Orchestrator.

Runs the complete engineering context pipeline:
  1. Discover GN DXF
  2. Parse all engineering parameters
  3. Build EngineeringContext
  4. Validate
  5. Run audit (17 criteria)
  6. Export JSON artefacts

MODEL_VERSION: 7.5.0
"""
from __future__ import annotations
import pathlib
from datetime import datetime
from typing import Any, Dict, List

from .engineering_context_factory    import EngineeringContextFactory
from .engineering_context_loader     import EngineeringContextLoader
from .engineering_context_validator  import EngineeringContextValidator
from .engineering_context_audit      import EngineeringContextAudit
from .engineering_context_statistics import EngineeringContextStatistics
from .engineering_context_writer     import EngineeringContextWriter


class PhaseR2AOrchestrator:

    def __init__(self, v7_root: pathlib.Path, output_dir: pathlib.Path):
        self._v7  = v7_root
        self._out = output_dir

    def run(self) -> Dict[str, Any]:
        print(f"\n{'='*70}")
        print("  PHASE R.2A — Engineering Context Runtime Parsing & Injection")
        print(f"  MODEL_VERSION 7.5.0  |  {datetime.utcnow().isoformat()}")
        print(f"  READ + PARSE + BUILD + INJECT (no calc changes)")
        print(f"{'='*70}\n")

        # ------------------------------------------------------------------
        # Step 1: Discover + build
        # ------------------------------------------------------------------
        print("[1/5] Discovering GN DXF and building EngineeringContext ...")
        ctx, validation_passed, val_warnings = (
            EngineeringContextFactory.create_from_registry(self._v7)
        )

        if ctx is None:
            print("  ERROR: GN DXF not found — cannot build EngineeringContext.")
            return {"status": "FAIL", "reason": "GN DXF not found"}

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
        print(f"\n[5/5] Exporting 6 JSON artefacts to: {self._out}")
        writer = EngineeringContextWriter(self._out)
        paths = writer.write_all(ctx, loader, validation_passed, val_warnings)
        for name, path in paths.items():
            print(f"     {name}: {path}")

        # ------------------------------------------------------------------
        # Final summary
        # ------------------------------------------------------------------
        self._print_final(audit_results, passed_count, total_count, ctx, loader)

        return {
            "status": "PASS" if passed_count == total_count else "PARTIAL",
            "audit_score": f"{passed_count}/{total_count}",
            "validation_passed": validation_passed,
            "primary_steel_grade": ctx.primary_steel_grade,
            "cover_beam_mm": loader.get_cover("BEAM"),
            "dl_table_entries": len(ctx.development_length_table),
            "parse_confidence": ctx.parse_confidence,
            "export_paths": paths,
        }

    def _print_final(self, audit_results, passed, total, ctx, loader):
        print(f"\n{'='*70}")
        print(f"  PHASE R.2A COMPLETE")
        print(f"{'='*70}")
        print(f"  Audit score:       {passed}/{total}")
        print(f"  Parse confidence:  {ctx.parse_confidence:.1%}")
        print(f"\n  ENGINEERING CONTEXT (from GN DXF):")
        print(f"    Primary steel grade  : {ctx.primary_steel_grade}")
        print(f"    Beam concrete grade  : {loader.get_concrete_grade('BEAM')}")
        print(f"    Beam cover           : {loader.get_cover('BEAM')}mm")
        print(f"    Ld factor (dia12/M30): {loader.get_development_length_factor('M30')}d")
        print(f"    Ld dia=12, M30       : {loader.get_development_length_mm(12,'M30')}mm")
        print(f"    Ld dia=16, M30       : {loader.get_development_length_mm(16,'M30')}mm")
        print(f"    Ld dia=20, M30       : {loader.get_development_length_mm(20,'M30')}mm")
        print(f"    Hook 135° multiple   : {loader.get_hook_multiple(135)}d")
        print(f"    Std 90° bend         : {loader.get_standard_bend_multiple()}xd")
        print(f"    Min lap              : {loader.get_minimum_lap_mm()}mm")
        print(f"\n  PIPELINE IMPACT vs. HARDCODED CONSTANTS:")
        print(f"    Cover  : pipeline=40mm -> GN={loader.get_cover('BEAM')}mm  (delta={loader.get_cover('BEAM')-40:+d}mm)")
        gn_dl  = loader.get_development_length_mm(12)
        pi_dl  = 40 * 12
        print(f"    Ld dia12: pipeline={pi_dl}mm -> GN={gn_dl}mm  (delta={gn_dl-pi_dl:+d}mm)")
        print(f"    Steel  : pipeline=Fe415 -> GN={ctx.primary_steel_grade}")
        print(f"{'='*70}\n")
