"""
Phase GN.1 Orchestrator — master pipeline for the General Notes Context Audit.

Executes Parts 1-10 in sequence, collects all artefacts, and writes 10 JSON
output files.

MODEL_VERSION: 7.4.0
READ-ONLY: no engineering calculations or production logic are modified.
"""
from __future__ import annotations
import pathlib
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from .gn_discovery             import GeneralNotesDiscovery
from .gn_extractor             import GNExtractor
from .gn_context_builder       import EngineeringContextBuilder
from .framing_plan_auditor     import FramingPlanAuditor
from .reinforcement_drawing_auditor import ReinforcementDrawingAuditor
from .hardcoded_default_detector    import HardcodedDefaultDetector
from .engineering_gap_analyzer      import EngineeringGapAnalyzer
from .project_generalization_checker import ProjectGeneralizationChecker
from .gn_validation_rules      import GNValidationRules
from .gn_reporter              import GNReporter
from .gn_export                import GNExport


class PhaseGN1Orchestrator:
    """
    Runs the full GN.1 audit pipeline.
    """

    def __init__(self, v7_root: pathlib.Path, output_dir: pathlib.Path):
        self._v7 = v7_root
        self._out = output_dir

    # ------------------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        print(f"\n{'='*70}")
        print("  PHASE GN.1 — General Notes Engineering Context Audit")
        print(f"  MODEL_VERSION 7.4.0  |  {datetime.utcnow().isoformat()}")
        print(f"  READ-ONLY AUDIT — no production code modified")
        print(f"{'='*70}\n")

        # ----------------------------------------------------------
        # PART 1: GN Discovery
        # ----------------------------------------------------------
        print("[1/10] General Notes DXF Discovery ...")
        discovery_engine = GeneralNotesDiscovery(self._v7)
        discovery = discovery_engine.discover()
        self._report_step("Discovery", {
            "GN DXF": discovery.gn_dxf_path,
            "Method": discovery.discovery_method,
            "Dynamic": discovery.discovered_dynamically,
            "Text entities": discovery.total_text_entities,
        })

        # ----------------------------------------------------------
        # PART 2: GN Extraction
        # ----------------------------------------------------------
        print("[2/10] General Notes Parameter Extraction ...")
        extracted: List[Any] = []
        if discovery.gn_dxf_path != "NOT_FOUND":
            gn_path = pathlib.Path(discovery.gn_dxf_path)
            extractor = GNExtractor(gn_path)
            extracted = extractor.extract()
        self._report_step("Extraction", {"Parameters extracted": len(extracted)})

        # ----------------------------------------------------------
        # PART 3: Engineering Context & Traceability
        # ----------------------------------------------------------
        print("[3/10] Engineering Context Builder & Traceability ...")
        ctx_builder = EngineeringContextBuilder()
        traceability = ctx_builder.build_traceability(extracted)
        consumption = ctx_builder.build_consumption_matrix(extracted)
        self._report_step("Context", {
            "Traceability nodes": len(traceability),
            "Consumption records": len(consumption),
        })

        # ----------------------------------------------------------
        # PART 4: Framing Plan Audit
        # ----------------------------------------------------------
        print("[4/10] Framing Plan Audit ...")
        framing_auditor = FramingPlanAuditor(self._v7)
        framing = framing_auditor.audit()
        self._report_step("Framing", {
            "Fields audited": len(framing),
            "Fields in use": sum(1 for f in framing if f.used),
        })

        # ----------------------------------------------------------
        # PART 5: Reinforcement Drawing Audit
        # ----------------------------------------------------------
        print("[5/10] Reinforcement Drawing Audit ...")
        rebar_auditor = ReinforcementDrawingAuditor(self._v7)
        rebar = rebar_auditor.audit()
        self._report_step("Reinforcement", {
            "Fields audited": len(rebar),
            "Fields consumed": sum(1 for r in rebar if r.used),
        })

        # ----------------------------------------------------------
        # PART 6: Hardcoded Default Detector
        # ----------------------------------------------------------
        print("[6/10] Hardcoded Default Detector ...")
        detector = HardcodedDefaultDetector(self._v7)
        hardcoded = detector.detect()
        self._report_step("Hardcoded", {
            "Hardcoded constants found": len(hardcoded),
        })

        # ----------------------------------------------------------
        # PART 7: (Consumption matrix already built in Part 3)
        # ----------------------------------------------------------
        print("[7/10] Consumption Validation (from context builder) ...")
        self._report_step("Consumption", {
            "Records": len(consumption),
            "All-consumed": sum(1 for c in consumption if c.all_match),
        })

        # ----------------------------------------------------------
        # PART 8: Engineering Gap Analysis
        # ----------------------------------------------------------
        print("[8/10] Engineering Gap Analysis ...")
        gap_analyzer = EngineeringGapAnalyzer()
        gaps = gap_analyzer.analyze(extracted, traceability, hardcoded)
        from .gn_models import GapSeverity
        self._report_step("Gaps", {
            "Total gaps": len(gaps),
            "CRITICAL": sum(1 for g in gaps if g.severity == GapSeverity.CRITICAL),
            "HIGH":     sum(1 for g in gaps if g.severity == GapSeverity.HIGH),
            "MEDIUM":   sum(1 for g in gaps if g.severity == GapSeverity.MEDIUM),
            "LOW":      sum(1 for g in gaps if g.severity == GapSeverity.LOW),
        })

        # ----------------------------------------------------------
        # PART 9: Project Generalization Check
        # ----------------------------------------------------------
        print("[9/10] Project Generalization Check ...")
        gen_checker = ProjectGeneralizationChecker(self._v7)
        generalization = gen_checker.check()
        self._report_step("Generalization", {
            "Verdict": generalization["verdict"],
            "Violations": len(generalization.get("hardcoded_violations", [])),
        })

        # ----------------------------------------------------------
        # PART 10: Validation Rules
        # ----------------------------------------------------------
        print("[10/10] Validation Rules (12 rules) ...")
        validator = GNValidationRules()
        validation = validator.evaluate(
            discovery, extracted, traceability,
            hardcoded, gaps, consumption, generalization
        )
        passed = sum(1 for v in validation if v.passed)
        total  = len(validation)
        self._report_step("Validation", {f"RULE_{i+1}": ("PASS" if v.passed else "FAIL")
                                          for i, v in enumerate(validation)})

        # ----------------------------------------------------------
        # Build master report
        # ----------------------------------------------------------
        reporter = GNReporter()
        full_report = reporter.build_report(
            discovery, extracted, traceability, framing, rebar,
            hardcoded, consumption, gaps, generalization, validation
        )
        full_report["timestamp"] = datetime.utcnow().isoformat()

        # ----------------------------------------------------------
        # Export all artefacts
        # ----------------------------------------------------------
        print(f"\nExporting artefacts to: {self._out}")
        exporter = GNExport(self._out)
        export_paths = exporter.export_all(
            discovery, extracted, traceability, framing, rebar,
            hardcoded, consumption, gaps, generalization, validation,
            full_report,
        )

        # ----------------------------------------------------------
        # Print final summary
        # ----------------------------------------------------------
        self._print_final_summary(validation, gaps, export_paths)

        return {
            "validation_score": f"{passed}/{total}",
            "all_rules_passed": passed == total,
            "verdict": full_report["overall_verdict"],
            "export_paths": export_paths,
            "gap_count": len(gaps),
            "extracted_count": len(extracted),
        }

    # ------------------------------------------------------------------
    def _report_step(self, step: str, data: Dict) -> None:
        parts = " | ".join(f"{k}: {v}" for k, v in data.items())
        print(f"     {step}: {parts}")

    def _print_final_summary(
        self,
        validation: List[Any],
        gaps: List[Any],
        paths: Dict[str, str],
    ) -> None:
        from .gn_models import GapSeverity
        passed = sum(1 for v in validation if v.passed)
        total  = len(validation)
        print(f"\n{'='*70}")
        print(f"  PHASE GN.1 COMPLETE")
        print(f"{'='*70}")
        print(f"  Validation:  {passed}/{total} rules passed")
        print(f"  Gaps found:  {len(gaps)}")
        print(f"    CRITICAL:  {sum(1 for g in gaps if g.severity == GapSeverity.CRITICAL)}")
        print(f"    HIGH:      {sum(1 for g in gaps if g.severity == GapSeverity.HIGH)}")
        print(f"    MEDIUM:    {sum(1 for g in gaps if g.severity == GapSeverity.MEDIUM)}")
        print(f"    LOW:       {sum(1 for g in gaps if g.severity == GapSeverity.LOW)}")
        print(f"  Artefacts:   {len(paths)} JSON files written")
        print(f"\n  KEY FINDING:")
        print(f"    GN DXF is DISCOVERED but NOT PARSED at runtime.")
        print(f"    Engineering constants are HARDCODED — values match GN for")
        print(f"    Benchmark Set 2 but will BREAK for different projects.")
        print(f"    Phase R.2 must implement live GN DXF parsing.")
        print(f"{'='*70}\n")
        for name, path in paths.items():
            print(f"  {name}: {path}")
