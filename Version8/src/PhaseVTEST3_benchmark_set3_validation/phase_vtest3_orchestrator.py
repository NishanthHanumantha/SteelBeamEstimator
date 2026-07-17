"""
phase_vtest3_orchestrator.py — Master orchestrator for Phase V.TEST.3.
MODEL_VERSION: 8.1.1

READ-ONLY validation. Executes complete pipeline on Benchmark Set 3.
"""
from __future__ import annotations

import pathlib
from datetime import datetime
from typing import Dict

from benchmark3_artifact_collector import Benchmark3ArtifactCollector
from benchmark3_export import Benchmark3Export
from benchmark3_generalization_auditor import Benchmark3GeneralizationAuditor
from benchmark3_loader import Benchmark3Loader
from benchmark3_models import FullBenchmark3Result
from benchmark3_pipeline_runner import Benchmark3PipelineRunner
from benchmark3_readiness_scorer import Benchmark3ReadinessScorer
from benchmark3_reporter import Benchmark3Reporter
from benchmark3_statistics import Benchmark3Statistics
from benchmark3_validator import Benchmark3Validator

MODEL_VERSION = "8.1.1"
PHASE_ID      = "V.TEST.3"
BENCHMARK_ID  = "BENCHMARK::DRAWING_3_V8"


class BENCHMARK_SET3_VALIDATION_ERROR(RuntimeError):
    pass


class PhaseVTEST3Orchestrator:

    def __init__(self) -> None:
        self._result = FullBenchmark3Result(
            model_version=MODEL_VERSION,
            benchmark_id=BENCHMARK_ID,
            timestamp=datetime.now().isoformat(),
        )

    def run(self) -> FullBenchmark3Result:
        print("=" * 72)
        print("Phase V.TEST.3 — Benchmark Set 3 Generalization Validation")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print(f"BENCHMARK_ID  : {BENCHMARK_ID}")
        print("READ-ONLY — No engineering logic modified")
        print("=" * 72)

        # Step 1: Load Benchmark Set 3
        print("\n[1/6] Loading Benchmark Set 3 input files ...")
        loader   = Benchmark3Loader()
        manifest = loader.load()
        loader.export_manifest(manifest)
        self._result.manifest = manifest
        print(f"  Files: {manifest.total_files}, DXF: {manifest.dxf_count}")
        print(f"  Project: {manifest.project_name}, Building: {manifest.building}, Floor: {manifest.floor}")
        if manifest.issues:
            for iss in manifest.issues:
                print(f"  [WARN] {iss}")

        # Step 2: Execute complete pipeline
        print("\n[2/6] Executing complete production pipeline ...")
        runner   = Benchmark3PipelineRunner()
        pipeline = runner.run_all()
        self._result.pipeline = pipeline
        print(f"  Stages: {pipeline.stages_passed}/{pipeline.stages_executed} passed "
              f"({pipeline.total_elapsed_seconds:.1f}s)")

        # Step 3: Collect artefacts
        print("\n[3/6] Collecting pipeline artefacts ...")
        collector = Benchmark3ArtifactCollector()
        data      = collector.collect_all()
        self._result.discovery_summary      = data["discovery"]
        self._result.beam_summary           = data["beams"]
        self._result.general_notes_summary  = data["general_notes"]
        self._result.reinforcement_summary  = data["reinforcement"]
        self._result.interpretation_summary = data["interpretation"]
        self._result.engineering_bar_summary= data["engineering_bars"]
        self._result.production_summary     = data["production"]
        self._result.warnings               = collector.collect_warnings()

        # Step 4: Generalization audit
        print("\n[4/6] Running generalization audit ...")
        auditor = Benchmark3GeneralizationAuditor()
        audit   = auditor.audit()
        self._result.generalization_audit = audit
        print(f"  {audit['summary']}")

        # Step 5: Readiness score + validation
        print("\n[5/6] Computing readiness score and validation rules ...")
        scorer = Benchmark3ReadinessScorer()
        scores, overall, classification = scorer.score(
            beams=data["beams"],
            gn=data["general_notes"],
            reinf=data["reinforcement"],
            interp=data["interpretation"],
            bars=data["engineering_bars"],
            prod=data["production"],
            pipeline={
                "success_rate_pct": pipeline.success_rate_pct,
                "pipeline_completed": pipeline.pipeline_completed,
                "stages_passed": pipeline.stages_passed,
                "stages_executed": pipeline.stages_executed,
            },
            audit=audit,
        )
        self._result.readiness_scores         = scores
        self._result.overall_readiness_score  = overall
        self._result.readiness_classification = classification

        validator = Benchmark3Validator()
        validation = validator.validate(
            discovery=data["discovery"],
            beams=data["beams"],
            gn=data["general_notes"],
            interp=data["interpretation"],
            bars=data["engineering_bars"],
            prod=data["production"],
            pipeline={
                "pipeline_completed": pipeline.pipeline_completed,
                "stages_passed": pipeline.stages_passed,
                "stages_executed": pipeline.stages_executed,
            },
            audit=audit,
        )
        self._result.validation_rules = validation["rules"]
        self._result.overall_passed   = validation["all_pass"]
        print(f"  Readiness: {overall}/100 — {classification}")
        print(f"  Validation: {validation['summary']}")

        # Step 6: Export
        print("\n[6/6] Exporting validation artefacts ...")
        stats_module = Benchmark3Statistics()
        statistics   = stats_module.collect(
            pipeline=pipeline,
            discovery=data["discovery"],
            beams=data["beams"],
            reinf=data["reinforcement"],
            interp=data["interpretation"],
            bars=data["engineering_bars"],
            prod=data["production"],
            readiness_scores=scores,
            overall_score=overall,
        )
        reporter    = Benchmark3Reporter()
        json_report = reporter.build_json_report(self._result)
        md_report   = reporter.generate_markdown(self._result)
        exporter    = Benchmark3Export()
        paths       = exporter.export_all(self._result, statistics, json_report, md_report)
        for name, p in paths.items():
            print(f"  {name}")

        print()
        print("=" * 72)
        print(f"V.TEST.3 COMPLETE — {validation['summary']}")
        print(f"Readiness: {overall}/100 ({classification})")
        print("=" * 72)

        return self._result
