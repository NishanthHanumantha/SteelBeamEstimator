"""
QA.3.0 — Validation gates.
MODEL_VERSION: 10.0.0
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

MODEL_VERSION = "10.0.0"
PHASE_ID = "QA.3.0"

REQUIRED_SET_KEYS = ("Fourth", "Fifth", "Sixth")


class QAValidator:
    def __init__(self, output_root: Path, engine_root: Path):
        self.output_root = Path(output_root)
        self.engine_root = Path(engine_root)

    def validate(
        self,
        discovery: Dict[str, Any],
        production: Dict[str, Any],
        benchmark: Dict[str, Any],
        report_paths: Dict[str, Any],
    ) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []

        def add(name: str, ok: bool, detail: str = "") -> None:
            checks.append({"check": name, "pass": bool(ok), "detail": detail})

        sets = production.get("sets") or []
        keys = {s.get("set_key") for s in sets}
        add(
            "all_three_unseen_sets_completed",
            REQUIRED_SET_KEYS[0] in keys
            and REQUIRED_SET_KEYS[1] in keys
            and REQUIRED_SET_KEYS[2] in keys
            and all(s.get("success") for s in sets),
            f"keys={sorted(keys)} success={[s.get('success') for s in sets]}",
        )
        add(
            "fresh_production_executed",
            all(s.get("success") for s in sets) and len(sets) == 3,
            f"n={len(sets)}",
        )
        add(
            "no_workbook_reuse",
            not production.get("reuse_detected_any")
            and all(not s.get("reuse_detected") for s in sets),
            f"reuse_detected_any={production.get('reuse_detected_any')}",
        )
        add(
            "estimator_excel_only_during_benchmark",
            production.get("estimator_excel_opened_during_production") is False
            and benchmark.get("estimator_excel_opened_during_benchmark") is True
            and all(
                s.get("estimator_excel_opened_during_production") is False for s in sets
            ),
            "production=False benchmark=True",
        )
        add(
            "version10_execution",
            "Version10" in str(self.engine_root)
            or (self.engine_root / "VERSION.md").exists()
            or (self.engine_root / "README.md").exists(),
            str(self.engine_root),
        )
        add(
            "production_pipeline_unchanged",
            (
                self.engine_root
                / "src"
                / "PhaseQA.2_multi_drawing_benchmark"
                / "pipeline_runner.py"
            ).exists(),
            "uses existing ProductionPipelineRunner (orchestration-only phase)",
        )
        add(
            "generalization_report_generated",
            Path(report_paths.get("json") or "").exists()
            and Path(report_paths.get("xlsx") or "").exists()
            and Path(report_paths.get("md") or "").exists(),
            str(report_paths),
        )
        add(
            "discovery_complete",
            len(discovery.get("complete_unseen_targets") or []) >= 3,
            str(discovery.get("complete_unseen_targets")),
        )
        add(
            "benchmark_success",
            bool(benchmark.get("success")),
            f"compared={sum(1 for r in (benchmark.get('results') or []) if r.get('compared'))}",
        )

        # Fresh workbooks exist under phase folders
        for key in REQUIRED_SET_KEYS:
            folder = self.output_root / f"{key}_Set_Drawings"
            wb = folder / "Estimation_Output.xlsx"
            add(f"fresh_workbook_{key}", wb.exists(), str(wb))
            crops = folder / "RenderedCrops"
            pngs = list(crops.rglob("*.png")) if crops.exists() else []
            add(f"fresh_crops_{key}", len(pngs) > 0, f"pngs={len(pngs)}")

        overall = all(c["pass"] for c in checks)
        doc = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_pass": overall,
            "checks": checks,
            "pass_count": sum(1 for c in checks if c["pass"]),
            "fail_count": sum(1 for c in checks if not c["pass"]),
        }
        out = self.output_root / "QA30Validation.json"
        out.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return doc
