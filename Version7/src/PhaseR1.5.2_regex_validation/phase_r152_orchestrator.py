"""Phase R.1.5.2 master orchestrator — READ-ONLY regex validation."""
from __future__ import annotations

import json
import pathlib
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .engineering_notation_validator import EngineeringNotationValidator
from .mtext_cleaning_trace import MtextCleaningTrace
from .pattern_classifier import PatternClassifier
from .pattern_inventory import PatternInventory
from .raw_text_inventory import RawTextInventory
from .regex_coverage_analyzer import RegexCoverageAnalyzer
from .regex_match_validator import RegexMatchValidator
from .regex_statistics import RegexStatistics
from .regex_validation_export import RegexValidationExport
from .regex_validation_reporter import RegexValidationReporter
from .regex_validation_validator import RegexValidationValidator
from .unsupported_pattern_detector import UnsupportedPatternDetector


class PhaseR152Orchestrator:

    MODEL_VERSION = "7.8.3"
    DXF_REL = (
        "data/Benchmark_Set_2/reinforcement/"
        "Galera_GF_BeamReinforcementDetails.dxf"
    )
    REGISTRY_REL = (
        "data/output/PhaseVROOT.1_dynamic_pipeline_initialization/beam_registry.json"
    )
    R1_ANNOTATIONS_REL = (
        "data/output/PhaseR.1_generalized_reinforcement_discovery/"
        "reinforcement_annotations.json"
    )

    def __init__(
        self,
        v7_root: pathlib.Path,
        output_dir: Optional[pathlib.Path] = None,
    ):
        self._v7 = v7_root
        self._out = output_dir or (
            v7_root / "data/output/PhaseR1.5.2_regex_validation"
        )

    def run(self) -> Dict[str, Any]:
        t0 = time.perf_counter()
        print(f"\n{'='*70}")
        print("  PHASE R.1.5.2 - Reinforcement Pattern Coverage & Regex Validation")
        print(f"  MODEL_VERSION {self.MODEL_VERSION}  |  {datetime.utcnow().isoformat()}")
        print("  READ-ONLY FORENSIC REGEX AUDIT")
        print(f"{'='*70}\n")

        registry = self._read_json(self._v7 / self.REGISTRY_REL)
        dxf_path = self._v7 / self.DXF_REL
        r1_ann = self._flatten_r1_annotations(
            self._read_json(self._v7 / self.R1_ANNOTATIONS_REL)
        )

        print("[1/8] Raw DXF text inventory ...")
        entities = RawTextInventory(dxf_path, registry).build()
        print(f"      Entities: {len(entities)}")

        print("\n[2/8] MTEXT cleaning trace ...")
        cleaner = MtextCleaningTrace()
        clean_map = cleaner.build_clean_map(entities)
        mtext_traces = cleaner.trace_all(entities)
        clean_text_map = {k: v.cleaned_text for k, v in clean_map.items()}
        lost = sum(1 for c in clean_map.values() if c.status == "ENGINEERING_TEXT_LOST")
        print(f"      MTEXT traced: {len(mtext_traces)}  engineering lost: {lost}")

        print("\n[3/8] Pattern inventory ...")
        patterns = PatternInventory().build(entities, clean_text_map)
        print(f"      Unique patterns: {len(patterns)}")

        print("\n[4/8] Regex validation ...")
        validator = RegexMatchValidator()
        matches = validator.validate_all(entities, clean_map)
        matches = PatternClassifier().apply_all(entities, matches, clean_text_map)
        matched = sum(1 for m in matches if m.matched)
        print(f"      Matched: {matched}/{len(matches)}")

        print("\n[5/8] Unsupported pattern detection ...")
        unsupported = UnsupportedPatternDetector().detect(entities, matches, patterns)
        print(f"      Unsupported: {len(unsupported)}")

        print("\n[6/8] Engineering notation validation ...")
        match_dict = {m.entity_id: m for m in matches}
        eng_records = EngineeringNotationValidator().validate_all(
            entities, clean_map, match_dict
        )
        print(f"      Engineering notations: {len(eng_records)}")

        print("\n[7/8] Coverage metrics (Y10/stirrup/spacer) ...")
        stats = RegexStatistics().compute(entities, clean_map, matches, r1_ann)
        coverage = RegexCoverageAnalyzer().analyze(
            patterns, matches, clean_map, eng_records, unsupported, stats
        )
        print(f"      Regex coverage: {coverage.get('regex_coverage_pct')}%")
        print(f"      Parser readiness: {coverage.get('parser_readiness_score')}")

        print("\n[8/8] Validation and export ...")
        validation = RegexValidationValidator().validate(
            entities, mtext_traces, patterns, matches, unsupported,
            stats, coverage, coverage.get("root_cause_counts", {}),
        )
        print(f"      Validation: {validation['score']}")

        reporter = RegexValidationReporter()
        markdown = reporter.build_markdown(
            stats, coverage, validation, unsupported, stats.get("y10", {})
        )

        artefacts = {
            "raw_text_inventory.json": {
                "total": len(entities),
                "items": [e.to_dict() for e in entities],
            },
            "mtext_cleaning_trace.json": {
                "total": len(mtext_traces),
                "items": [t.to_dict() for t in mtext_traces],
            },
            "pattern_inventory.json": {
                "total": len(patterns),
                "items": [p.to_dict() for p in patterns],
            },
            "regex_validation.json": {
                "total": len(matches),
                "matched": matched,
                "failed": len(matches) - matched,
            },
            "regex_match_results.json": {
                "items": [m.to_dict() for m in matches],
            },
            "unsupported_patterns.json": {
                "total": len(unsupported),
                "items": unsupported,
            },
            "engineering_notation_validation.json": {
                "total": len(eng_records),
                "items": [e.to_dict() for e in eng_records],
            },
            "y10_coverage_audit.json": stats.get("y10", {}),
            "stirrup_coverage_audit.json": stats.get("stirrup", {}),
            "spacer_coverage_audit.json": stats.get("spacer", {}),
            "regex_statistics.json": stats,
            "coverage_summary.json": coverage,
            "root_cause_report.json": {
                "counts": coverage.get("root_cause_counts", {}),
                "failures": [
                    m.to_dict() for m in matches if not m.matched
                ][:50],
            },
            "regex_validation_report.json": {
                "model_version": self.MODEL_VERSION,
                "statistics": stats,
                "coverage": coverage,
                "validation": validation,
                "unsupported_count": len(unsupported),
            },
        }
        export_paths = RegexValidationExport(self._out).export_all(artefacts, markdown)

        elapsed = round(time.perf_counter() - t0, 3)
        status = "PASS" if validation["all_passed"] else "FAIL"
        self._print_final(stats, coverage, validation, elapsed, status)

        return {
            "status": status,
            "model_version": self.MODEL_VERSION,
            "statistics": stats,
            "coverage": coverage,
            "validation": validation,
            "unsupported": unsupported,
            "export_paths": export_paths,
            "elapsed_seconds": elapsed,
        }

    @staticmethod
    def _read_json(path: pathlib.Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _flatten_r1_annotations(data: Dict[str, Any]) -> List[Dict]:
        items = []
        for beam_id, anns in data.get("by_beam", {}).items():
            for ann in anns:
                ann = dict(ann)
                ann["beam_id"] = beam_id
                items.append(ann)
        return items

    def _print_final(self, stats, coverage, validation, elapsed, status):
        y10 = stats.get("y10", {})
        print(f"\n{'='*70}")
        print(f"  PHASE R.1.5.2 COMPLETE — {status}")
        print(f"  DXF entities: {stats.get('total_dxf_entities', 0)}")
        print(f"  Reinforcement candidates: {stats.get('reinforcement_candidates', 0)}")
        print(f"  Regex matched: {stats.get('regex_matched', 0)}")
        print(f"  Coverage: {coverage.get('overall_coverage_pct')}%")
        print(f"  Y10 DXF: {y10.get('dxf_entities', 0)}  parsed: {y10.get('parsed', 0)}")
        print(f"  Validation: {validation['score']}")
        print(f"  Time: {elapsed}s")
        print(f"{'='*70}\n")
        for rid in sorted(validation["rules"].keys()):
            r = validation["rules"][rid]
            print(f"    {rid}: {r['status']} — {r['detail']}")
