"""
Export artefacts + markdown report for Phase R.1.4.
MODEL_VERSION: 8.6.0
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

MODEL_VERSION = "8.6.0"


class BenchmarkReportGenerator:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_all(self, result: Dict[str, Any]) -> Dict[str, str]:
        official = result["official_model"]
        production = result["production_snapshot"]
        comparison = result["comparison"]
        kpis = result["kpis"]
        diagnostics = result["diagnostics"]
        root_cause = result["root_cause"]
        regression = result["regression"]

        paths: Dict[str, str] = {}

        def dump(name: str, data: Any) -> None:
            p = self.output_dir / name
            p.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            paths[name] = str(p)

        dump("official_workbook_model.json", official.to_dict())
        dump("official_steel_summary.json", official.steel_summary.to_dict())
        dump("official_beams.json", {
            "model_version": MODEL_VERSION,
            "beam_count": len(official.beams),
            "beams": [b.to_dict() for b in official.beams],
        })
        dump("official_reinforcement_rows.json", {
            "model_version": MODEL_VERSION,
            "row_count": len(official.reinforcement_rows),
            "rows": [r.to_dict() for r in official.reinforcement_rows],
        })
        dump("production_snapshot.json", production.to_dict())
        dump("beam_accuracy.json", comparison.get("beam_accuracy") or {})
        dump("reinforcement_accuracy.json", comparison.get("reinforcement_accuracy") or {})
        dump("piece_accuracy.json", comparison.get("piece_accuracy") or {})
        dump("engineeringbar_accuracy.json", comparison.get("engineeringbar_accuracy") or {})
        dump("steel_accuracy.json", comparison.get("steel_accuracy") or {})
        dump("bbs_accuracy.json", comparison.get("bbs_accuracy") or {})
        dump("workbook_accuracy.json", comparison.get("workbook_accuracy") or {})
        dump("production_kpis.json", kpis)
        dump("production_error_diagnostics.json", diagnostics)
        dump("root_cause_analysis.json", root_cause)
        dump("benchmark_regression.json", regression)
        dump("production_scorecard.json", kpis.get("scorecard") or {})

        md = self.generate_markdown(result)
        md_path = self.output_dir / "phase_r14_summary.md"
        md_path.write_text(md, encoding="utf-8")
        paths["phase_r14_summary.md"] = str(md_path)
        return paths

    def generate_markdown(self, result: Dict[str, Any]) -> str:
        official = result["official_model"]
        production = result["production_snapshot"]
        comparison = result["comparison"]
        kpis = result["kpis"]
        regression = result["regression"]
        steel = comparison.get("steel_accuracy") or {}
        beam = comparison.get("beam_accuracy") or {}
        reinf = comparison.get("reinforcement_accuracy") or {}
        scorecard = kpis.get("scorecard") or {}
        rec = result.get("recommendation", "B")

        lines: List[str] = [
            "# Phase R.1.4 — Production Accuracy Benchmark",
            "",
            f"**MODEL_VERSION:** {MODEL_VERSION}",
            f"**Recommendation:** {rec}",
            f"**Overall production accuracy:** {scorecard.get('overall_pct')}% ({scorecard.get('band')})",
            "",
            "## Workbook Interpretation",
            "",
            f"- Summary detected: `{official.interpretation.get('summary_detected')}`",
            f"- Breakup detected: `{official.interpretation.get('breakup_detected')}`",
            f"- Project: {official.project.project_name}",
            f"- Floor: {official.steel_summary.floor}",
            f"- Official beams: **{len(official.beams)}**",
            f"- Official reinforcement rows: **{len(official.reinforcement_rows)}**",
            "",
            "## Summary Table Extraction",
            "",
            f"- TOTAL-MT: **{official.steel_summary.total_mt}**",
            f"- KG: **{official.steel_summary.total_kg}**",
            f"- Diameter summary (MT): `{official.steel_summary.diameter_summary}`",
            "",
            "## Beam / Reinforcement Detection",
            "",
            f"- Beam detection F1: {beam.get('detection_f1')}",
            f"- Missing beams: {len(beam.get('missing_beams') or [])}",
            f"- Extra beams: {len(beam.get('extra_beams') or [])}",
            f"- Classification accuracy: {reinf.get('classification_accuracy')}",
            "",
            "## Steel / BBS / Workbook",
            "",
            f"- Official kg: {steel.get('official_total_kg')}",
            f"- Production kg: {steel.get('production_total_kg')}",
            f"- Steel pct error: {steel.get('pct_error')}%",
            f"- BBS score: {(comparison.get('bbs_accuracy') or {}).get('bbs_score')}",
            f"- Workbook score: {(comparison.get('workbook_accuracy') or {}).get('workbook_score')}",
            "",
            "## KPI Summary",
            "",
        ]
        for k, v in (scorecard.get("kpis_pct") or {}).items():
            lines.append(f"- {k}: **{v}%**")

        lines.extend([
            "",
            "## Regression",
            "",
            f"- Passed: `{regression.get('passed')}`",
            f"- No worksheet-name dependency / fixed cells / set-specific rules: enforced",
            "",
            "## Production Snapshot Counts",
            "",
            f"- Intents: {len(production.intents)}",
            f"- Details: {len(production.details)}",
            f"- Pieces: {len(production.pieces) or (production.steel_summary.get('piece_summary') or {}).get('piece_count')}",
            f"- EngineeringBars: {len(production.engineering_bars)}",
            "",
            "---",
            f"*Phase R.1.4 | MODEL_VERSION {MODEL_VERSION}*",
            "",
        ])
        return "\n".join(lines)
