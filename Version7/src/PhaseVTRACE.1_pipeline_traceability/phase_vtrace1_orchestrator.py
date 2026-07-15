"""
phase_vtrace1_orchestrator.py — Main orchestrator for Phase V.TRACE.1.
MODEL_VERSION: 7.1.2  |  READ-ONLY — no engineering logic modified.

Executes the 10-module pipeline traceability framework and produces
9 exported JSON artefacts plus a printed engineering trace report.
"""

from __future__ import annotations
import sys
import yaml
import pathlib
from datetime import datetime, timezone
from typing import Dict, List

from . import MODEL_VERSION, PHASE_ID
from .stage_snapshot_collector  import StageSnapshotCollector
from .beam_identity_tracker      import BeamIdentityTracker
from .stage_comparator           import StageComparator
from .lifecycle_tracker          import LifecycleTracker
from .beam_loss_detector         import BeamLossDetector
from .duplication_detector       import DuplicationDetector
from .pipeline_flow_analyzer     import PipelineFlowAnalyzer
from .root_cause_locator         import RootCauseLocator
from .trace_validator            import TraceValidator
from .trace_statistics           import TraceStatisticsEngine
from .trace_reporter             import TraceReporter
from .trace_export               import TraceExporter

WORKSPACE  = pathlib.Path(r"C:\Users\nishanth.h\SteelBeamEstimator")
CONFIG_FILE = WORKSPACE / "Version7/config/pipeline_traceability.yaml"


def _load_config() -> dict:
    return yaml.safe_load(CONFIG_FILE.read_text("utf-8"))


def run() -> int:
    cfg          = _load_config()
    stage_cfgs   = cfg["pipeline_stages"]
    stage_order  = [s["id"] for s in stage_cfgs]

    print("=" * 72)
    print(f"Phase {PHASE_ID} — End-to-End Beam Traceability & Pipeline Flow Audit")
    print(f"MODEL_VERSION : {MODEL_VERSION}")
    print(f"Stages        : {stage_order}")
    print("=" * 72)

    # ──────────────────────────────────────────────────────────────────
    # MODULE 1: Stage Snapshot Collector
    # ──────────────────────────────────────────────────────────────────
    print("\n[MODULE 1]  Collecting stage snapshots ...")
    collector  = StageSnapshotCollector(stage_cfgs)
    snapshots  = collector.collect_all()
    for sid, snap in snapshots.items():
        status = "OK" if snap.artefact_exists else "MISSING"
        print(f"  [{status}]  {sid:<14} {snap.beam_count:>5} beams  |  {snap.output_file[-60:]}")

    # ──────────────────────────────────────────────────────────────────
    # MODULE 2: Beam Identity Tracker
    # ──────────────────────────────────────────────────────────────────
    print("\n[MODULE 2]  Building beam identity lifecycle map ...")
    tracker    = BeamIdentityTracker(stage_order)
    lifecycles = tracker.build_lifecycle_map(snapshots, source_stage="VROOT1")
    print(f"  Beams tracked: {len(lifecycles)}")

    # ──────────────────────────────────────────────────────────────────
    # MODULE 3: Stage Comparator
    # ──────────────────────────────────────────────────────────────────
    print("\n[MODULE 3]  Comparing consecutive stages ...")
    comparator   = StageComparator()
    comparisons  = comparator.compare_all(snapshots, stage_order)
    for c in comparisons:
        icon = "==" if c.delta == 0 else ("vv" if c.delta < 0 else "^^")
        print(f"  {icon}  {c.from_stage:<14} -> {c.to_stage:<14}  "
              f"{c.from_count:>4} -> {c.to_count:>4}  "
              f"(d{c.delta:+d}, removed={len(c.beams_removed)})")

    # ──────────────────────────────────────────────────────────────────
    # MODULE 4: Pipeline Flow Analyzer (early, needed for loss detector)
    # ──────────────────────────────────────────────────────────────────
    print("\n[MODULE 4]  Analyzing pipeline flow ...")
    flow_analyzer = PipelineFlowAnalyzer(stage_order)
    flow          = flow_analyzer.build_flow(snapshots, comparisons)
    print(f"  First failure stage: {flow.get('first_failure_stage', 'None')}")
    print(f"  First failure delta: {flow.get('first_failure_delta', 0):+d}")

    # ──────────────────────────────────────────────────────────────────
    # MODULE 5: Beam Loss Detector
    # ──────────────────────────────────────────────────────────────────
    print("\n[MODULE 5]  Detecting beam loss ...")
    loss_detector = BeamLossDetector(stage_order, snapshots)
    lost_beams    = loss_detector.detect(lifecycles)
    # Update lifecycle loss_category after detection
    for lc in lifecycles.values():
        pass  # already mutated in-place by detect()
    print(f"  Lost beams: {len(lost_beams)}")
    if lost_beams:
        from collections import Counter
        cats = Counter(lb.loss_category.value for lb in lost_beams)
        for cat, cnt in cats.items():
            print(f"    {cat}: {cnt}")

    # ──────────────────────────────────────────────────────────────────
    # MODULE 6: Duplication Detector
    # ──────────────────────────────────────────────────────────────────
    print("\n[MODULE 6]  Detecting duplicates ...")
    dup_detector = DuplicationDetector()
    duplicates   = dup_detector.detect_all(snapshots)
    print(f"  Duplicate records: {len(duplicates)}")

    # ──────────────────────────────────────────────────────────────────
    # Lifecycle Tracker (build matrix)
    # ──────────────────────────────────────────────────────────────────
    lc_tracker       = LifecycleTracker(stage_order)
    lifecycle_matrix = lc_tracker.build_matrix(lifecycles)

    # ──────────────────────────────────────────────────────────────────
    # MODULE 7: Root Cause Locator
    # ──────────────────────────────────────────────────────────────────
    print("\n[MODULE 7]  Locating root causes ...")
    rc_locator   = RootCauseLocator(snapshots)
    root_causes  = rc_locator.locate_all(lost_beams, flow.get("comparisons", []))
    for rc in root_causes:
        print(f"  [{rc.failure_category.value}]  Stage '{rc.stage_id}'  "
              f"-> {len(rc.affected_beams)} beams lost  ({rc.confidence})")

    # ──────────────────────────────────────────────────────────────────
    # MODULE 8: Statistics
    # ──────────────────────────────────────────────────────────────────
    print("\n[MODULE 8]  Computing statistics ...")
    stats_engine = TraceStatisticsEngine()
    statistics   = stats_engine.compute(
        snapshots, lifecycles, lost_beams, duplicates, flow, stage_order
    )
    print(f"  Source beams          : {statistics.total_beams_at_source}")
    print(f"  Pipeline retention    : {statistics.pipeline_retention_pct:.1f}%")
    print(f"  Total lost beams      : {statistics.total_lost_beams}")
    print(f"  Stages with loss      : {statistics.stages_with_loss}")

    # ──────────────────────────────────────────────────────────────────
    # MODULE 9: Validator
    # ──────────────────────────────────────────────────────────────────
    print("\n[MODULE 9]  Validating trace ...")
    validator  = TraceValidator()
    validation = validator.validate(
        snapshots, lifecycles, lost_beams, duplicates,
        root_causes, flow, statistics.to_dict(), stage_order,
    )
    passed = sum(1 for v in validation if v.get("status") == "PASS")
    failed = sum(1 for v in validation if v.get("status") == "FAIL")
    warned = sum(1 for v in validation if v.get("status") == "WARN")
    for v in validation:
        icon = "[PASS]" if v["status"] == "PASS" else ("[WARN]" if v["status"] == "WARN" else "[FAIL]")
        print(f"  {icon}  {v['rule']}: {v['title']}")
        if v["status"] != "PASS":
            print(f"         >> {v['detail']}")

    # ──────────────────────────────────────────────────────────────────
    # MODULE 10/11: Reporter
    # ──────────────────────────────────────────────────────────────────
    print("\n[MODULE 10] Building engineering trace report ...")
    reporter = TraceReporter()
    report   = reporter.build(
        snapshots, lifecycles, lost_beams, duplicates,
        root_causes, flow, statistics, validation,
        lifecycle_matrix, stage_order,
    )

    # ──────────────────────────────────────────────────────────────────
    # MODULE 12: Export
    # ──────────────────────────────────────────────────────────────────
    print("\n[MODULE 11] Exporting artefacts ...")
    exporter   = TraceExporter()
    export_map = exporter.export_all(
        snapshots, lifecycles, lost_beams, duplicates,
        root_causes, flow, statistics, validation,
        lifecycle_matrix, report,
    )

    # ──────────────────────────────────────────────────────────────────
    # Final printed flow diagram
    # ──────────────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("PIPELINE FLOW DIAGRAM")
    print("=" * 72)
    for row in flow["flow_rows"]:
        first_fail_mark = ""
        if flow.get("first_failure_stage") and row["stage_id"] == flow["first_failure_stage"]:
            first_fail_mark = "  <-- FIRST FAILURE (beam count drops here)"
        cnt = str(row["beam_count"]) if row["artefact_exists"] else "MISSING"
        print(f"  {row['stage_id']:<14}  {cnt:>6} beams{first_fail_mark}")
        print("       |")

    print("\n" + "=" * 72)
    print(f"V.TRACE.1 COMPLETE  |  Rules: {passed}/10 PASS | {warned} WARN | {failed} FAIL")
    print(f"First failure stage  : {flow.get('first_failure_stage', 'NONE')}")
    print(f"Total lost beams     : {len(lost_beams)}")
    print(f"Root cause category  : {root_causes[0].failure_category.value if root_causes else 'NONE'}")
    print(f"Output dir           : {exporter.OUTPUT_DIR if hasattr(exporter, 'OUTPUT_DIR') else 'see above'}")
    print("=" * 72)

    if root_causes:
        print("\nENGINEERING RECOMMENDATION:")
        print(report["sections"]["8_engineering_recommendations"][0]["action"])

    return 0 if failed == 0 else 1
