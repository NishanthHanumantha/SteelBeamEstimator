"""Export Phase R.1.3 piece-generation artefacts. MODEL_VERSION: 8.5.0"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict


class PieceExporter:
    OUT_DIR_NAME = "PhaseR1_3_reinforcement_piece_generation"

    def __init__(self, v7_root: pathlib.Path):
        self._out = v7_root / "data/output" / self.OUT_DIR_NAME
        self._out.mkdir(parents=True, exist_ok=True)

    def export_all(self, result: Dict[str, Any], report_md: str) -> Dict[str, str]:
        written = {}
        payload = result.get("payload") or {}
        payloads = {
            "reinforcement_pieces.json": {
                "model_version": result.get("model_version"),
                "piece_count": len(result.get("pieces") or []),
                "pieces": result.get("pieces") or [],
            },
            "piece_summary.json": {
                "model_version": result.get("model_version"),
                "detail_count": payload.get("detail_count"),
                "piece_count": payload.get("piece_count"),
                "piece_types": payload.get("piece_types"),
            },
            "piece_geometry.json": payload.get("geometry_summary") or {},
            "piece_validation.json": payload.get("validation") or {},
            "piece_confidence.json": payload.get("confidence") or {},
            "piece_traceability.json": {
                "model_version": result.get("model_version"),
                "entries": payload.get("traceability") or [],
            },
            "piece_types.json": {
                "histogram": payload.get("piece_types") or {},
            },
            "piece_generation_report.json": {
                "model_version": result.get("model_version"),
                "validation": result.get("validation"),
                "regression": result.get("regression"),
                "payload_meta": {
                    k: payload.get(k)
                    for k in (
                        "detail_count",
                        "piece_count",
                        "piece_types",
                        "geometry_summary",
                        "development_summary",
                    )
                },
            },
            "engineeringbar_piece_mapping.json": {
                "model_version": result.get("model_version"),
                "mappings": result.get("mapping") or [],
            },
            "benchmark_regression_piece_generation.json": result.get("regression") or {},
        }
        for name, data in payloads.items():
            path = self._out / name
            path.write_text(
                json.dumps(data, indent=2, default=str, ensure_ascii=False),
                encoding="utf-8",
            )
            written[name] = str(path)
        md = self._out / "phase_r13_summary.md"
        md.write_text(report_md, encoding="utf-8")
        written["phase_r13_summary.md"] = str(md)
        return written

    def generate_report(self, result: Dict[str, Any]) -> str:
        val = result.get("validation") or {}
        payload = result.get("payload") or {}
        reg = result.get("regression") or {}
        rec = result.get("recommendation", "B")
        lines = [
            "# Phase R.1.3 — Reinforcement Piece Generation Engine",
            "",
            "**MODEL_VERSION:** 8.5.0",
            f"**Validation:** {val.get('passed', 0)}/{val.get('total', 8)} rules passed",
            f"**Recommendation:** {rec}",
            "",
            "## Executive Summary",
            "",
            "ReinforcementPiece is the manufacturing layer between ReinforcementDetail "
            "and EngineeringBar. Details expand into fabricated pieces (including "
            "stirrup zones and both-support extras). EngineeringBarBuilder consumes "
            "pieces only.",
            "",
            f"- Details: **{payload.get('detail_count')}**",
            f"- Pieces: **{payload.get('piece_count')}**",
            f"- Mean confidence: **{(payload.get('confidence') or {}).get('mean')}**",
            "",
            "## Pipeline",
            "",
            "```",
            "Intent -> Detail -> Piece -> EngineeringBar -> Steel -> BBS",
            "```",
            "",
            "## Piece Statistics / Types",
            "",
            f"`{payload.get('piece_types')}`",
            "",
            "## Geometry / Development Validation",
            "",
            f"- Geometry: `{payload.get('geometry_summary')}`",
            f"- Development: `{payload.get('development_summary')}`",
            f"- Piece validation passed: `{(payload.get('validation') or {}).get('passed')}`",
            "",
            "## Piece Confidence",
            "",
            f"`{payload.get('confidence')}`",
            "",
            "## EngineeringBar Integration",
            "",
            f"- Builder uses pieces: **{result.get('builder_uses_pieces')}**",
            f"- Mapping entries: **{len(result.get('mapping') or [])}**",
            "",
            "## Regression",
            "",
            f"- No regression: {reg.get('no_regression')}",
            f"- Summary: {reg.get('summary')}",
            "",
            "## Remaining Risks",
            "",
            "- Support-zone length fractions (0.25L) are generalized when span is known.",
            "- Stock-length / lap optimisation deferred to later phases.",
            "",
            "## Exported Artefacts",
            "",
        ]
        for name in (
            "reinforcement_pieces.json",
            "piece_summary.json",
            "piece_geometry.json",
            "piece_validation.json",
            "piece_confidence.json",
            "piece_traceability.json",
            "piece_types.json",
            "piece_generation_report.json",
            "engineeringbar_piece_mapping.json",
            "benchmark_regression_piece_generation.json",
            "phase_r13_summary.md",
        ):
            lines.append(f"- `{self.OUT_DIR_NAME}/{name}`")
        lines.extend(["", "## Recommendation", ""])
        if rec == "A":
            lines.append(
                "**Recommendation A** — Ready for Phase R.1.4 — "
                "Engineering Steel & BBS Accuracy Benchmark Engine"
            )
        else:
            lines.append(
                "**Recommendation B** — Minor fixes required before benchmarking."
            )
        lines.extend(["", "---", "*Phase R.1.3 Piece Generation | MODEL_VERSION 8.5.0*", ""])
        return "\n".join(lines)
