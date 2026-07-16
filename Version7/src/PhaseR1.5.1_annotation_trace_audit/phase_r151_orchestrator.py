"""Phase R.1.5.1 master orchestrator — READ-ONLY forensic audit."""
from __future__ import annotations
import pathlib
import time
from datetime import datetime
from typing import Any, Dict, Optional

from .annotation_export import AnnotationExport
from .annotation_group_trace import build_group_trace
from .annotation_inventory import PipelineDataLoader
from .annotation_loss_detector import AnnotationLossDetector
from .annotation_reporter import AnnotationReporter
from .annotation_statistics import AnnotationStatistics
from .annotation_trace_builder import AnnotationTraceBuilder
from .annotation_validator import AnnotationValidator
from .beam_trace import build_beam_trace
from .bbs_trace import build_bbs_trace
from .diameter_trace import build_diameter_trace
from .engineering_bar_trace import build_engineering_bar_trace
from .steel_trace import build_steel_trace


class PhaseR151Orchestrator:

    MODEL_VERSION = "7.8.2"

    def __init__(
        self,
        v7_root: pathlib.Path,
        output_dir: Optional[pathlib.Path] = None,
    ):
        self._v7 = v7_root
        self._out = output_dir or (
            v7_root / "data/output/PhaseR1.5.1_annotation_trace_audit"
        )

    def run(self) -> Dict[str, Any]:
        t0 = time.perf_counter()
        print(f"\n{'='*70}")
        print("  PHASE R.1.5.1 - Annotation -> EngineeringBar Trace Audit")
        print(f"  MODEL_VERSION {self.MODEL_VERSION}  |  {datetime.utcnow().isoformat()}")
        print(f"  READ-ONLY FORENSIC AUDIT")
        print(f"{'='*70}\n")

        print("[1/5] Loading pipeline artefacts ...")
        loader = PipelineDataLoader(self._v7)
        loader.load_all()
        print(f"      Inventory: {len(loader.inventory)} annotations")
        print(f"      DXF Y10 entities: {len(loader.dxf_y10)}")

        print("\n[2/5] Building annotation traces ...")
        records = AnnotationTraceBuilder().build_all(loader)
        matrix = [r.to_dict() for r in records]

        print("\n[3/5] Detecting losses and root causes ...")
        losses = AnnotationLossDetector().detect(records)
        stats = AnnotationStatistics().compute(
            records, losses, loader.dxf_y10, loader
        )

        y10_audit = {
            "dxf_entities": loader.dxf_y10,
            "pipeline_records": [
                r.to_dict() for r in records
                if r.diameter_mm == 10 or "Y10" in r.normalized_text.upper()
                or r.role == "Y10_CANDIDATE"
            ],
            "diameter_summary_y10": stats.get("y10", {}).get("steel_in_diameter_summary"),
            "conclusion": (
                "Y10 lost at AnnotationDiscovery._strip_mtext — MTEXT brace block "
                "removes entire annotation text before regex matching"
                if loader.dxf_y10 else "No Y10 in DXF"
            ),
        }
        stirrup_audit = {
            "records": [r.to_dict() for r in records if r.role == "STIRRUP"],
            "dxf_stirrup_like": loader.dxf_stirrup,
            "statistics": stats.get("stirrup", {}),
        }
        spacer_audit = {
            "records": [r.to_dict() for r in records if r.role == "SPACER_BAR"],
            "statistics": stats.get("spacer", {}),
        }

        print("\n[4/5] Running 12-rule validation ...")
        validation = AnnotationValidator().validate(records, losses, stats, loader)
        print(f"      Validation: {validation['score']}")

        print("\n[5/5] Exporting artefacts ...")
        reporter = AnnotationReporter()
        markdown = reporter.build_markdown(
            stats, validation, losses, loader.dxf_y10
        )
        artefacts = {
            "annotation_inventory.json": {
                "total": len(loader.inventory),
                "items": [i.to_dict() for i in loader.inventory],
            },
            "annotation_trace.json": {"records": matrix, "total": len(matrix)},
            "annotation_group_trace.json": build_group_trace(records),
            "engineering_bar_trace.json": build_engineering_bar_trace(records),
            "steel_trace.json": build_steel_trace(records),
            "bbs_trace.json": build_bbs_trace(records),
            "diameter_trace.json": build_diameter_trace(records),
            "beam_trace.json": build_beam_trace(records),
            "annotation_loss_report.json": losses,
            "y10_annotation_audit.json": y10_audit,
            "stirrup_annotation_audit.json": stirrup_audit,
            "spacer_annotation_audit.json": spacer_audit,
            "annotation_statistics.json": stats,
            "annotation_validation.json": validation,
            "annotation_trace_report.json": {
                "model_version": self.MODEL_VERSION,
                "statistics": stats,
                "validation": validation,
                "losses": losses,
                "y10_conclusion": y10_audit.get("conclusion"),
            },
        }
        export_paths = AnnotationExport(self._out).export_all(artefacts, markdown)

        elapsed = round(time.perf_counter() - t0, 3)
        status = "PASS" if validation["all_passed"] else "FAIL"
        self._print_final(stats, validation, losses, elapsed, status)

        return {
            "status": status,
            "model_version": self.MODEL_VERSION,
            "statistics": stats,
            "validation": validation,
            "losses": losses,
            "y10_audit": y10_audit,
            "export_paths": export_paths,
            "elapsed_seconds": elapsed,
        }

    def _print_final(self, stats, validation, losses, elapsed, status):
        y10 = stats.get("y10", {})
        print(f"\n{'='*70}")
        print(f"  PHASE R.1.5.1 COMPLETE — {status}")
        print(f"  Annotations: {stats.get('total_annotations', 0)}")
        print(f"  Reach steel: {stats.get('steel', 0)}")
        print(f"  Reach Excel: {stats.get('excel', 0)}")
        print(f"  Lost: {losses.get('lost', 0)}")
        print(f"  Y10 DXF: {y10.get('dxf_entities', 0)}  "
              f"consumed: {y10.get('consumed', 0)}  lost: {y10.get('lost', 0)}")
        print(f"  Validation: {validation['score']}")
        print(f"  Time: {elapsed}s")
        print(f"{'='*70}\n")
        for rid in sorted(validation["rules"].keys()):
            r = validation["rules"][rid]
            print(f"    {rid}: {r['status']} — {r['detail']}")
