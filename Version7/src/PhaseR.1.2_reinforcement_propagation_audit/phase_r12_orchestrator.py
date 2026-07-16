"""
Phase R.1.2 Orchestrator — Reinforcement Propagation Audit
MODEL_VERSION: 7.3.2 — READ-ONLY
"""
from __future__ import annotations
import pathlib
import time
from datetime import datetime
from typing import Any, Dict

from .reinforcement_model_reader import ReinforcementModelReader
from .adapter_trace import AdapterTrace
from .engineering_bar_trace import EngineeringBarTrace
from .steel_weight_trace import SteelWeightTrace
from .bbs_trace import BBSTrace
from .beam_summary_trace import BeamSummaryTrace
from .propagation_comparator import PropagationComparator
from .missing_bar_detector import MissingBarDetector, RootCauseLocator
from .propagation_statistics import PropagationStatistics
from .propagation_validator import PropagationValidator
from .propagation_reporter import PropagationReporter
from .propagation_export import PropagationExport


class PhaseR12Orchestrator:

    def __init__(self, v7_root: pathlib.Path, output_dir: pathlib.Path):
        self._v7 = v7_root
        self._out = output_dir

    def run(self) -> Dict[str, Any]:
        t0 = time.perf_counter()
        print(f"\n{'='*70}")
        print("  PHASE R.1.2 — Reinforcement Propagation Audit")
        print(f"  MODEL_VERSION 7.3.2  |  {datetime.utcnow().isoformat()}")
        print(f"  READ-ONLY — no engineering logic modifications")
        print(f"{'='*70}\n")

        print("[1/6] Loading pipeline artefacts ...")
        reader = ReinforcementModelReader(self._v7)
        reader.load_all()
        beam_count = len(reader.beam_ids())
        print(f"      Beams in registry: {beam_count}")
        for key, path in reader.paths.items():
            status = "OK" if path else "MISSING"
            print(f"      {key:10s}: {status}")

        print("\n[2/6] Building per-beam propagation matrix ...")
        comparator = PropagationComparator()
        records = comparator.build_matrix(reader)
        comparison = comparator.compare_r1_vs_workbook(reader)

        locator = RootCauseLocator()
        records = locator.locate(records, reader)
        root_cause_report = locator.report(records)
        matrix = [r.to_dict() for r in records]

        print(f"      R.1 beams with groups: {sum(1 for r in records if r.r1_total_quantity > 0)}")
        print(f"      L.2 beams with bars:   {sum(1 for r in records if r.l2_bar_count > 0)}")
        print(f"      Steel weight > 0:      {sum(1 for r in records if r.steel_weight_kg > 0)}")

        print("\n[3/6] Running stage traces ...")
        adapter_trace = AdapterTrace().trace(reader)
        eng_trace = EngineeringBarTrace().trace(reader)
        steel_trace = SteelWeightTrace().trace(reader)
        bbs_trace = BBSTrace().trace(reader)
        excel_trace = BeamSummaryTrace().trace(reader)
        missing_report = MissingBarDetector().detect(records)

        print("\n[4/6] Computing statistics ...")
        statistics = PropagationStatistics().compute(records, comparison)
        print(f"      Overall propagation: {statistics['overall_propagation_pct']}%")
        print(f"      R.1 qty -> L.2 bars loss: {statistics['engineering_bars_lost_r1_to_l2']}")

        print("\n[5/6] Running 10-rule validation ...")
        validator = PropagationValidator()
        results = validator.validate(
            records, adapter_trace, eng_trace, steel_trace,
            bbs_trace, excel_trace, root_cause_report, reader.paths,
        )
        passed = sum(1 for r in results if r.passed)
        for r in results:
            st = "PASS" if r.passed else "FAIL"
            print(f"      [{st}] {r.rule_id}: {r.description}")

        print(f"\n[6/6] Exporting artefacts to: {self._out}")
        reporter = PropagationReporter()
        full_report = reporter.build_report(
            records, root_cause_report, statistics, comparison, results
        )
        exporter = PropagationExport(self._out)
        paths = exporter.write_all(
            matrix, adapter_trace, eng_trace, steel_trace, bbs_trace,
            excel_trace, missing_report, root_cause_report, statistics,
            results, full_report,
        )
        for name, path in paths.items():
            print(f"      {name}: {path}")

        elapsed = time.perf_counter() - t0
        all_pass = passed == len(results)

        print(f"\n{'='*70}")
        print(f"  PHASE R.1.2 COMPLETE")
        print(f"  Validation: {passed}/{len(results)}")
        print(f"  Primary root cause:")
        print(f"    {root_cause_report.get('primary_systemic_root_cause', '')[:120]}")
        print(f"  Execution time: {elapsed:.2f}s")
        print(f"  Status: {'PASS' if all_pass else 'FAIL'}")
        print(f"{'='*70}\n")

        return {
            "status": "PASS" if all_pass else "FAIL",
            "validation_score": f"{passed}/{len(results)}",
            "beam_count": beam_count,
            "beams_with_steel": sum(1 for r in records if r.steel_weight_kg > 0),
            "primary_root_cause": root_cause_report.get("primary_systemic_root_cause"),
            "execution_time_s": round(elapsed, 3),
            "export_paths": paths,
        }
