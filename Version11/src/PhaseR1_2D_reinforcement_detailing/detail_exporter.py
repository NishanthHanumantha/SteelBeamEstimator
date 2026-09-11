"""Export Phase R.1.2D artefacts."""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict


class DetailExporter:
    OUT_DIR_NAME = "PhaseR1_2D_reinforcement_detailing"

    def __init__(self, v7_root: pathlib.Path):
        self._out = v7_root / "data/output" / self.OUT_DIR_NAME
        self._out.mkdir(parents=True, exist_ok=True)

    def export_all(self, result: Dict[str, Any], report_md: str) -> Dict[str, str]:
        written = {}
        payloads = {
            "reinforcement_details.json": {
                "model_version": result.get("model_version"),
                "detail_count": len(result.get("details") or []),
                "details": result.get("details") or [],
            },
            "stirrup_zone_segments.json": {
                "model_version": result.get("model_version"),
                "segments": (result.get("payload") or {}).get("stirrup_segments") or [],
            },
            "support_zone_summary.json": (result.get("payload") or {}).get(
                "support_zone_summary"
            )
            or {},
            "continuity_summary.json": {
                "histogram": (result.get("payload") or {}).get("continuity_summary") or {}
            },
            "development_length_summary.json": (result.get("payload") or {}).get(
                "development_length_summary"
            )
            or {},
            "curtailment_summary.json": {
                "histogram": (result.get("payload") or {}).get("curtailment_summary") or {}
            },
            "side_face_detection.json": (result.get("payload") or {}).get(
                "side_face_detection"
            )
            or {},
            "detail_consistency_report.json": (result.get("payload") or {}).get(
                "consistency"
            )
            or {},
            "detail_confidence_summary.json": (result.get("payload") or {}).get(
                "confidence"
            )
            or {},
            "engineering_bar_detail_mapping.json": {
                "model_version": result.get("model_version"),
                "mappings": result.get("mapping") or [],
            },
        }
        for name, data in payloads.items():
            path = self._out / name
            path.write_text(
                json.dumps(data, indent=2, default=str, ensure_ascii=False),
                encoding="utf-8",
            )
            written[name] = str(path)
        md = self._out / "reinforcement_detailing_report.md"
        md.write_text(report_md, encoding="utf-8")
        written["reinforcement_detailing_report.md"] = str(md)
        return written

    def generate_report(self, result: Dict[str, Any]) -> str:
        val = result.get("validation") or {}
        payload = result.get("payload") or {}
        conf = payload.get("confidence") or {}
        cons = payload.get("consistency") or {}
        reg = result.get("regression") or {}
        rec = result.get("recommendation", "B")
        lines = [
            "# Phase R.1.2D — Reinforcement Detailing Interpretation Engine",
            "",
            "**MODEL_VERSION:** 8.4.0",
            f"**Validation:** {val.get('passed', 0)}/{val.get('total', 8)} rules passed",
            f"**Recommendation:** {rec}",
            "",
            "## Executive Summary",
            "",
            "R.1.2D introduces `ReinforcementDetail` between EngineeringIntent and "
            "EngineeringBar. Detailing (stirrup zones, support regions, continuity, "
            "Ld, curtailment, side-face) is resolved once and consumed exclusively "
            "by EngineeringBarBuilder.",
            "",
            f"- Details: **{len(result.get('details') or [])}**",
            f"- Stirrup segments: **{len(payload.get('stirrup_segments') or [])}**",
            f"- Mean confidence: **{conf.get('mean')}**",
            f"- Consistency critical flags: **{cons.get('critical_count')}**",
            "",
            "## Pipeline Changes",
            "",
            "```",
            "EngineeringIntent -> ReinforcementDetail -> EngineeringBar -> Steel -> BBS",
            "```",
            "",
            "## Detail Objects Generated",
            "",
            f"- Count: {len(result.get('details') or [])}",
            f"- Beams: {(payload.get('beam_count'))}",
            "",
            "## Stirrup Segments",
            "",
            f"- Segments exported: {len(payload.get('stirrup_segments') or [])}",
            "",
            "## Support Zones",
            "",
            f"`{payload.get('support_zone_summary')}`",
            "",
            "## Development Length Summary",
            "",
            f"`{payload.get('development_length_summary')}`",
            "",
            "## Curtailment Summary",
            "",
            f"`{payload.get('curtailment_summary')}`",
            "",
            "## Side Face Detection",
            "",
            f"`{payload.get('side_face_detection')}`",
            "",
            "## Consistency Validation",
            "",
            f"- Passed: {cons.get('passed')}",
            f"- Flags: {cons.get('flag_count')} (critical={cons.get('critical_count')})",
            f"- Histogram: `{cons.get('flag_histogram')}`",
            "",
            "## Confidence Distribution",
            "",
            f"`{conf}`",
            "",
            "## EngineeringBar Integration",
            "",
            "EngineeringBarBuilder consumes ReinforcementDetail only when the "
            "detail engine is available (Intent → Detail → Bar).",
            "",
            "## Regression Results",
            "",
            f"- No regression: {reg.get('no_regression')}",
            f"- Summary: {reg.get('summary')}",
            "",
            "## Recommendations",
            "",
        ]
        if rec == "A":
            lines.append(
                "**Recommendation A** — Detailing layer stable; proceed to "
                "production accuracy benchmarking / next engineering phase."
            )
        elif rec == "C":
            lines.append(
                "**Recommendation C** — Critical detailing defects; hold further phases."
            )
        else:
            lines.append(
                "**Recommendation B** — Additional detailing interpretation improvements required."
            )
        lines.extend(["", "---", "*Phase R.1.2D | MODEL_VERSION 8.4.0*", ""])
        return "\n".join(lines)
