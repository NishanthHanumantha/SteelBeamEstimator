"""
phase_r1_1_orchestrator.py — Master orchestrator for Phase R.1.1.

Pipeline:
  1. Reinforcement Source Adapter  (R.1 → L.2 format)
  2. Production Pipeline Runner    (SteelWeight + BBS + Excel)
  3. Production Comparator         (new vs previous V.RUN.1)
  4. Accuracy Statistics           (RMSE, MAE, MAPE, coverage)
  5. Improvement Analyzer          (verdict + recommendation)
  6. Validation Reporter           (10 rules)
  7. Engineering Reporter          (8-section report)
  8. Export                        (7 JSON artefacts)

No engineering logic is modified.  Only the reinforcement source changes.
MODEL_VERSION: 7.3.1
"""

from __future__ import annotations

import json
import logging
import pathlib
import sys
import time
from typing import Optional

import yaml

from .reinforcement_source_adapter import ReinforcementSourceAdapter
from .production_pipeline_runner   import ProductionPipelineRunner
from .production_comparator        import ProductionComparator
from .accuracy_statistics          import AccuracyStatistics
from .improvement_analyzer         import ImprovementAnalyzer
from .validation_reporter          import ValidationReporter, EngineeringReporter

log = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        level   = logging.INFO,
        format  = "%(asctime)s  [%(levelname)-7s]  %(name)s — %(message)s",
        datefmt = "%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force   = True,
    )
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass


def _load_config(config_path: pathlib.Path) -> dict:
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _write_json(path: pathlib.Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


class PhaseR11Orchestrator:
    """Master orchestrator for Phase R.1.1."""

    def __init__(self, project_root: pathlib.Path):
        self.root        = project_root
        self._output_dir = project_root / "data/output/PhaseR.1.1_production_validation"
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # ── Paths ─────────────────────────────────────────────────────────────
        self._r1_models = (
            project_root
            / "data/output/PhaseR.1_generalized_reinforcement_discovery"
            / "beam_reinforcement_models.json"
        )
        self._registry = (
            project_root
            / "data/output/PhaseVROOT.1_dynamic_pipeline_initialization"
            / "beam_registry.json"
        )
        self._prev_sw = (
            project_root / "data/output/Production_Output" / "steel_weight_summary.json"
        )

    # ──────────────────────────────────────────────────────────────────────────
    def run(self) -> dict:
        t0 = time.perf_counter()
        log.info("=" * 72)
        log.info("Phase R.1.1 — Production Validation  MODEL_VERSION 7.3.1")
        log.info("=" * 72)

        # ── Step 1: Adapt R.1 models to L.2 format ────────────────────────────
        log.info("[1/8] Reinforcement Source Adapter ...")
        adapter = ReinforcementSourceAdapter(
            self._r1_models,
            self._registry,
            self._output_dir,
        )
        adapted_path = adapter.adapt()
        log.info("      Adapted models: %s", adapted_path.name)

        # ── Step 2: Run production pipeline ───────────────────────────────────
        log.info("[2/8] Production Pipeline Runner ...")
        runner = ProductionPipelineRunner(
            adapted_path,
            self._output_dir,
            self._registry,
        )
        pipeline_result = runner.run()
        new_sw    = pipeline_result["steel_weight"]
        excel_path = pathlib.Path(pipeline_result["excel_path"]) if pipeline_result.get("excel_path") else None

        # ── Step 3: Load previous V.RUN.1 output ─────────────────────────────
        log.info("[3/8] Loading previous V.RUN.1 output ...")
        prev_sw = json.loads(self._prev_sw.read_text(encoding="utf-8"))
        log.info(
            "      Prev: %.1f kg (%d beams with weight)",
            prev_sw.get("total_weight_kg", 0),
            sum(1 for b in prev_sw.get("beam_weights", []) if b.get("total_weight_kg", 0) > 0),
        )

        # ── Step 4: Compare ───────────────────────────────────────────────────
        log.info("[4/8] Production Comparator ...")
        comparator  = ProductionComparator()
        comparison  = comparator.compare(new_sw, prev_sw)

        # ── Step 5: Accuracy statistics ───────────────────────────────────────
        log.info("[5/8] Accuracy Statistics ...")
        acc_stats   = AccuracyStatistics()
        statistics  = acc_stats.compute(comparison)

        # ── Step 6: Improvement analysis ──────────────────────────────────────
        log.info("[6/8] Improvement Analyzer ...")
        analyzer    = ImprovementAnalyzer()
        improvement = analyzer.analyze(comparison, statistics)

        # ── Step 7: Validation ────────────────────────────────────────────────
        log.info("[7/8] Validation Reporter ...")
        val_reporter = ValidationReporter()
        validation   = val_reporter.validate(
            adapted_path, prev_sw, new_sw, comparison,
            statistics, improvement, excel_path, self._output_dir,
        )

        # ── Step 8: Engineering report ────────────────────────────────────────
        log.info("[8/8] Engineering Report ...")
        eng_reporter = EngineeringReporter()
        report       = eng_reporter.generate(
            new_sw, prev_sw, comparison, statistics, improvement, validation
        )

        # ── Export ────────────────────────────────────────────────────────────
        log.info("Exporting artefacts ...")
        _write_json(self._output_dir / "production_summary.json",         new_sw)
        _write_json(self._output_dir / "beam_accuracy.json",              comparison["beam_comparison"])
        _write_json(self._output_dir / "diameter_accuracy.json",          comparison["diameter_comparison"])
        _write_json(self._output_dir / "overall_accuracy.json",           statistics)
        _write_json(self._output_dir / "improvement_report.json",         improvement)
        _write_json(self._output_dir / "pipeline_validation.json",        validation.to_dict())
        _write_json(self._output_dir / "engineering_validation_report.json", report)

        # Markdown report
        self._write_markdown(statistics, improvement, validation)

        elapsed = round(time.perf_counter() - t0, 2)
        log.info("=" * 72)
        log.info("Phase R.1.1 COMPLETE in %.2fs", elapsed)
        log.info("  Previous coverage   : %.1f%%", statistics["coverage_pct_prev"])
        log.info("  New coverage        : %.1f%%", statistics["coverage_pct_new"])
        log.info("  Coverage gain       : +%.1f pp", statistics["coverage_improvement_pct"])
        log.info("  Newly covered beams : %d", statistics["newly_covered_beams"])
        log.info("  New total weight    : %.1f kg", statistics["new_total_weight_kg"])
        log.info("  Verdict             : %s", improvement["verdict"])
        log.info("  Validation          : %s (%d/10)", validation.overall, validation.passed)
        log.info("=" * 72)

        return {
            "status":        validation.overall,
            "model_version": "7.3.1",
            "elapsed_s":     elapsed,
            "statistics":    statistics,
            "improvement":   improvement,
            "validation":    validation.to_dict(),
        }

    # ──────────────────────────────────────────────────────────────────────────
    def _write_markdown(self, stats: dict, improvement: dict, validation) -> None:
        lines = [
            "# Phase R.1.1 — Production Validation Report",
            f"**MODEL_VERSION**: 7.3.1  |  **Validation**: {validation.overall} ({validation.passed}/10)",
            "",
            "## Coverage",
            f"| Metric | Previous (V.RUN.1) | New (R.1.1) | Change |",
            f"|--------|-------------------|-------------|--------|",
            f"| Coverage % | {stats['coverage_pct_prev']:.1f}% | {stats['coverage_pct_new']:.1f}% | **+{stats['coverage_improvement_pct']:.1f} pp** |",
            f"| Total Weight (kg) | {stats['prev_total_weight_kg']:.1f} | {stats['new_total_weight_kg']:.1f} | {stats['overall_weight_diff_kg']:+.1f} |",
            f"| Newly Covered Beams | — | {stats['newly_covered_beams']} | +{stats['newly_covered_beams']} |",
            "",
            "## Accuracy Metrics",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| RMSE (kg) | {stats['rmse_kg']} |",
            f"| MAE (kg)  | {stats['mae_kg']} |",
            f"| MAPE (%)  | {stats['mape_pct']} |",
            "",
            "## Improvement Verdict",
            f"**{improvement['verdict']}**",
            "",
            improvement.get("recommendation", ""),
            "",
            "## Validation Rules",
        ]
        for r in validation.rules:
            status_icon = "[PASS]" if r.status == "PASS" else "[WARN]" if r.status == "WARN" else "[FAIL]"
            lines.append(f"- {status_icon} {r.rule_id}: {r.name} — {r.message}")

        md_path = self._output_dir / "engineering_validation_report.md"
        md_path.write_text("\n".join(lines), encoding="utf-8")
        log.info("Markdown report: %s", md_path.name)


# ── Entry point ───────────────────────────────────────────────────────────────
def run_phase_r1_1(project_root: pathlib.Path) -> dict:
    _setup_logging()
    orch = PhaseR11Orchestrator(project_root)
    return orch.run()
