"""
QA.2B.0 — IntegrationQA + ExecutionSummary writers
MODEL_VERSION: 9.6.0
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

MODEL_VERSION = "9.6.0"
PHASE_ID = "QA.2B.0"

# Module versions of connected production stages (read-only stamps)
RENDERER_VERSION = "9.5.2"  # T1.8.2 adaptive extent (latest render path)
CROP_GENERATOR_VERSION = "9.3.3"  # T1 OpenCV crop generation
ENGINEERING_PIPELINE_VERSION = "9.3.0"  # production spine through VB1 + T1
BENCHMARK_VERSION = "9.3.0"  # QA.2A
OWNERSHIP_VERSION = "9.5.4"  # T1.8.3.1 shared scope dedup


class IntegrationQA:
    def __init__(self, output_root: Path):
        self.output_root = Path(output_root)

    def write(
        self,
        integration: Dict[str, Any],
        validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        sets = integration.get("sets") or []
        beam_count = sum(int(s.get("beam_count") or 0) for s in sets)
        crop_count = sum(int(s.get("crop_count") or 0) for s in sets)
        comparison_count = sum(int(s.get("comparison_count") or 0) for s in sets)
        missing_render = sum(int(s.get("missing_render_count") or 0) for s in sets)
        missing_crop = sum(int(s.get("missing_crop_count") or 0) for s in sets)

        qa = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "renderer_version": RENDERER_VERSION,
            "crop_generator_version": CROP_GENERATOR_VERSION,
            "engineering_pipeline_version": ENGINEERING_PIPELINE_VERSION,
            "ownership_engine_version": OWNERSHIP_VERSION,
            "benchmark_version": BENCHMARK_VERSION,
            "execution_success": bool(integration.get("success"))
            and bool(validation.get("overall_pass")),
            "beam_count_processed": beam_count,
            "crop_count_generated": crop_count,
            "comparison_count": comparison_count,
            "missing_render_count": missing_render,
            "missing_crop_count": missing_crop,
            "sets_processed": len(sets),
            "validation_overall_pass": validation.get("overall_pass"),
            "benchmark_success": (integration.get("benchmark") or {}).get("success"),
            "per_set": [
                {
                    "set_key": s.get("set_key"),
                    "run_root": s.get("run_root"),
                    "success": s.get("success"),
                    "beam_count": s.get("beam_count"),
                    "crop_count": s.get("crop_count"),
                    "comparison_count": s.get("comparison_count"),
                    "missing_render_count": s.get("missing_render_count"),
                    "missing_crop_count": s.get("missing_crop_count"),
                }
                for s in sets
            ],
        }
        path = self.output_root / "PipelineIntegrationQA.json"
        path.write_text(json.dumps(qa, indent=2), encoding="utf-8")
        return qa

    def write_execution_summary(
        self,
        integration: Dict[str, Any],
        validation: Dict[str, Any],
        qa: Dict[str, Any],
    ) -> Path:
        lines = [
            "# QA.2B.0 — Execution Summary",
            "",
            f"**MODEL_VERSION:** {MODEL_VERSION}",
            f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
            f"**Overall PASS:** {validation.get('overall_pass')}",
            "",
            "## Purpose",
            "",
            "Pipeline integration / execution integrity only. "
            "Engineering accuracy is not evaluated in this phase.",
            "",
            "## Versions connected",
            "",
            f"- Renderer (T1.8.2): `{qa.get('renderer_version')}`",
            f"- Crop generator (T1 OpenCV): `{qa.get('crop_generator_version')}`",
            f"- Engineering pipeline: `{qa.get('engineering_pipeline_version')}`",
            f"- Ownership / shared scope: `{qa.get('ownership_engine_version')}`",
            f"- Benchmark (QA.2A): `{qa.get('benchmark_version')}`",
            "",
            "## Totals",
            "",
            f"- Beams processed: **{qa.get('beam_count_processed')}**",
            f"- Crops resolved: **{qa.get('crop_count_generated')}**",
            f"- Comparisons ready: **{qa.get('comparison_count')}**",
            f"- Missing renders: **{qa.get('missing_render_count')}**",
            f"- Missing crops: **{qa.get('missing_crop_count')}**",
            f"- Benchmark execution success: **{qa.get('benchmark_success')}**",
            "",
            "## Per drawing set",
            "",
        ]
        for s in integration.get("sets") or []:
            lines.extend(
                [
                    f"### {s.get('set_key')} — `{Path(s.get('run_root') or '').name}`",
                    "",
                    f"- Success: `{s.get('success')}`",
                    f"- Beams: {s.get('beam_count')} | Crops: {s.get('crop_count')} | "
                    f"Comparisons: {s.get('comparison_count')}",
                    f"- Missing crop: {s.get('missing_crop_count')} | "
                    f"Missing render: {s.get('missing_render_count')}",
                    "",
                ]
            )
            chain = s.get("track1_chain") or {}
            for st in chain.get("stages") or []:
                flag = "SKIP" if st.get("skipped") else ("OK" if st.get("success") else "FAIL")
                err = f" — {st.get('error')}" if st.get("error") else ""
                lines.append(f"  - `{st.get('stage')}`: {flag}{err}")
            lines.append("")

        lines.extend(
            [
                "## Validation checks",
                "",
            ]
        )
        for name, ok in (validation.get("checks") or {}).items():
            lines.append(f"- [{'x' if ok else ' '}] {name}")
        lines.append("")

        path = self.output_root / "ExecutionSummary.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path
