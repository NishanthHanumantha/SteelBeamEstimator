"""Phase R.1.5 master orchestrator — READ-ONLY."""
from __future__ import annotations
import pathlib
import time
from collections import Counter
from datetime import datetime
from typing import Any, Dict, Optional

from .beam_total_trace import BeamTotalTrace
from .bbs_trace import BBSTrace
from .consumption_export import ConsumptionExport
from .consumption_reporter import ConsumptionReporter
from .consumption_statistics import ConsumptionStatistics
from .diameter_summary_trace import DiameterSummaryTrace
from .engineering_bar_loader import EngineeringBarLoader
from .engineering_consumption_validator import EngineeringConsumptionValidator
from .excel_trace import ExcelTrace
from .project_total_trace import ProjectTotalTrace
from .quantity_comparator import QuantityComparator
from .steel_weight_trace import SteelWeightTrace


class PhaseR15Orchestrator:

    MODEL_VERSION = "7.8.1"

    def __init__(
        self,
        v7_root: pathlib.Path,
        output_dir: Optional[pathlib.Path] = None,
    ):
        self._v7 = v7_root
        self._out = output_dir or (
            v7_root / "data/output/PhaseR1.5_engineering_consumption_validation"
        )

    def run(self) -> Dict[str, Any]:
        t0 = time.perf_counter()
        print(f"\n{'='*70}")
        print("  PHASE R.1.5 — Engineering Calculation Consumption Validation")
        print(f"  MODEL_VERSION {self.MODEL_VERSION}  |  {datetime.utcnow().isoformat()}")
        print(f"  READ-ONLY — no engineering logic modifications")
        print(f"{'='*70}\n")

        print("[1/5] Loading pipeline data (read-only) ...")
        loader = EngineeringBarLoader(self._v7)
        loader.load_all()
        print(f"      Engineering bars: {len(loader.traces)}")
        print(f"      Reference workbook: "
              f"{'YES' if loader.reference_workbook_path else 'NO'}")

        print("\n[2/5] Running consumption traces ...")
        steel_traces = SteelWeightTrace().trace(loader)
        bbs_traces = BBSTrace().trace(loader, steel_traces)
        dia_trace = DiameterSummaryTrace().trace(loader, steel_traces)
        beam_trace = BeamTotalTrace().trace(loader, steel_traces)
        project_trace = ProjectTotalTrace().trace(loader, steel_traces)
        excel_trace = ExcelTrace().trace(loader)

        consumed = sum(1 for t in steel_traces.values() if t.consumed)
        print(f"      Steel consumed: {consumed}/{len(loader.traces)}")
        print(f"      BBS consumed: {sum(1 for t in bbs_traces.values() if t.consumed)}")

        print("\n[3/5] Building consumption matrix and detecting losses ...")
        comparator = QuantityComparator()
        matrix = comparator.build_matrix(
            loader, steel_traces, bbs_traces, dia_trace,
            beam_trace, project_trace, excel_trace,
        )
        losses = comparator.detect_losses(matrix)
        qty_validation = comparator.quantity_validation(
            loader, steel_traces, dia_trace, excel_trace
        )

        root_cause_counts = dict(Counter(m.root_cause for m in matrix if m.root_cause))
        root_cause_report = {
            "counts": root_cause_counts,
            "skipped_bars": [
                {
                    "trace_id": m.trace_id,
                    "beam_id": m.beam_id,
                    "role": m.bar_role,
                    "reason": steel_traces[m.trace_id].skip_reason,
                }
                for m in matrix if m.steel == "NO"
            ],
            "reference_diameter_gaps": qty_validation.get(
                "reference_diameter_mismatches", []
            ),
            "reference_beam_gaps": qty_validation.get("reference_beam_mismatches", []),
        }

        print("\n[4/5] Running 12-rule validation ...")
        validator = EngineeringConsumptionValidator()
        validation = validator.validate(
            loader, steel_traces, bbs_traces, dia_trace,
            beam_trace, project_trace, matrix, losses,
        )
        stats = ConsumptionStatistics().compute(
            loader, steel_traces, bbs_traces, matrix, losses,
            qty_validation, validation,
        )

        passed = sum(1 for r in validation.rules.values() if r["passed"])
        print(f"      Validation: {passed}/{len(validation.rules)}")
        print(f"      Consumption: {stats['consumption_pct']}%")
        print(f"      Pipeline health: {stats['engineering_accuracy_score']}")

        print("\n[5/5] Exporting artefacts ...")
        reporter = ConsumptionReporter()
        summary = reporter.build_summary(stats, validation)
        markdown = reporter.build_markdown(
            stats, validation, qty_validation, losses,
            excel_trace, root_cause_counts,
        )
        export_paths = ConsumptionExport(self._out).export_all(
            loader.traces, steel_traces, bbs_traces, dia_trace,
            beam_trace, project_trace, excel_trace, qty_validation,
            stats, matrix, root_cause_report, validation, summary, markdown,
        )

        elapsed = round(time.perf_counter() - t0, 3)
        status = "PASS" if validation.all_passed else "FAIL"
        self._print_final(stats, validation, losses, excel_trace, elapsed, status)

        return {
            "status": status,
            "model_version": self.MODEL_VERSION,
            "validation": validation,
            "statistics": stats,
            "losses": losses,
            "qty_validation": qty_validation,
            "root_cause_report": root_cause_report,
            "export_paths": export_paths,
            "elapsed_seconds": elapsed,
        }

    def _print_final(
        self, stats, validation, losses, excel_trace, elapsed, status
    ) -> None:
        ref = excel_trace.get("reference_comparison", {})
        print(f"\n{'='*70}")
        print(f"  PHASE R.1.5 COMPLETE — {status}")
        print(f"  Bars loaded:     {stats.get('engineering_bars_loaded', 0)}")
        print(f"  Reach steel:     {stats.get('reach_steel', 0)}")
        print(f"  Reach BBS:       {stats.get('reach_bbs', 0)}")
        print(f"  Reach Excel:     {stats.get('reach_excel', 0)}")
        print(f"  Lost (steel):    {losses.get('lost_before_steel', 0)}")
        if ref:
            print(f"  Ref total delta: {ref.get('project_total_delta_kg', 'N/A')} kg")
            print(f"  Ref dia gaps:    {ref.get('diameter_mismatch_count', 0)}")
        print(f"  Validation:      "
              f"{sum(1 for r in validation.rules.values() if r['passed'])}"
              f"/{len(validation.rules)}")
        print(f"  Time:            {elapsed}s")
        print(f"{'='*70}\n")

        print("  Validation Rules:")
        for rule_id in sorted(validation.rules.keys()):
            r = validation.rules[rule_id]
            print(f"    {rule_id}: {r['status']} — {r['detail']}")
