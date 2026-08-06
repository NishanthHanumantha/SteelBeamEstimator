"""
Build RULE-012 coverage reports, dashboard, and summary artefacts.
MODEL_VERSION: 8.8.2
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from beam_coverage_model import MODEL_VERSION, RULE_ID, BeamCoverageRecord, ProjectCoverageMetrics


class CoverageReportBuilder:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build_all(
        self,
        records: List[BeamCoverageRecord],
        metrics: ProjectCoverageMetrics,
        diagnostics: List[Dict[str, Any]],
        validation: Dict[str, Any],
        regression: Dict[str, Any],
        rule012: Dict[str, Any],
        sources: Dict[str, Any],
        recommendation: str,
        elapsed_s: float,
    ) -> Dict[str, str]:
        beam_rows = [r.to_dict() for r in records]
        missing_ids = [r.beam_id for r in records if r.status == "FAIL"]
        root_causes = Counter(d.get("likely_missing_phase") or "UNKNOWN" for d in diagnostics)

        coverage_report = {
            "model_version": MODEL_VERSION,
            "phase": "R.1.6.2",
            "rule_id": RULE_ID,
            "title": "Mandatory Stirrup Coverage Validation Report",
            "engineering_invariant": (
                "For every beam there shall exist at least one stirrup representation "
                "across Intent → Detail → Piece → EngineeringBar."
            ),
            "detection_only": True,
            "automatic_correction": False,
            "production_modified": False,
            "metrics": metrics.to_dict(),
            "missing_beam_ids": missing_ids,
            "beam_count_checked": len(records),
            "sources": sources,
            "recommendation": recommendation,
            "elapsed_s": elapsed_s,
        }

        beam_validation = {
            "model_version": MODEL_VERSION,
            "rule_id": RULE_ID,
            "beam_count": len(beam_rows),
            "beams": beam_rows,
            "levels": {
                "project": metrics.to_dict(),
                "beam": [
                    {
                        "beam_id": r.beam_id,
                        "status": r.status,
                        "top": "YES" if r.top_exists else "NO",
                        "bottom": "YES" if r.bottom_exists else "NO",
                        "stirrups": "YES" if r.stirrup_exists else "NO",
                    }
                    for r in records
                ],
                "object": [
                    {
                        "beam_id": r.beam_id,
                        **r.object_level.to_dict(),
                    }
                    for r in records
                ],
            },
        }

        missing_report = {
            "model_version": MODEL_VERSION,
            "rule_id": RULE_ID,
            "missing_count": len(diagnostics),
            "missing_beam_ids": missing_ids,
            "diagnostics": diagnostics,
        }

        dashboard = {
            "model_version": MODEL_VERSION,
            "rule_id": RULE_ID,
            "total_beams": metrics.beam_count,
            "total_stirrup_families": metrics.detected_stirrup_families,
            "coverage_pct": metrics.coverage_pct,
            "missing_beams": metrics.beam_count - metrics.detected_stirrup_families,
            "validation_pass_pct": metrics.pass_pct,
            "validation_fail_pct": metrics.fail_pct,
            "root_cause_distribution": dict(root_causes),
            "phase_distribution": metrics.phase_distribution,
            "recommendation": recommendation,
        }

        statistics = {
            "model_version": MODEL_VERSION,
            "rule_id": RULE_ID,
            **metrics.to_dict(),
            "status_counts": {
                "PASS": metrics.pass_count,
                "FAIL": metrics.fail_count,
                "UNKNOWN": metrics.unknown_count,
            },
            "top_present_count": sum(1 for r in records if r.top_exists),
            "bottom_present_count": sum(1 for r in records if r.bottom_exists),
            "stirrup_pass_count": sum(1 for r in records if r.stirrup_exists),
        }

        rule_summary = {
            "model_version": MODEL_VERSION,
            "phase": "R.1.6.2",
            "rule": rule012,
            "validation": validation,
            "regression": regression,
            "dashboard": dashboard,
            "recommendation": recommendation,
            "mandatory_gate": {
                "before_steel_calculation": True,
                "before_benchmarking": True,
                "before_correction_engine": True,
            },
        }

        paths = {
            "stirrup_coverage_report.json": coverage_report,
            "beam_stirrup_validation.json": beam_validation,
            "missing_stirrup_beams.json": missing_report,
            "coverage_dashboard.json": dashboard,
            "coverage_statistics.json": statistics,
            "rule012_summary.json": rule_summary,
        }
        written: Dict[str, str] = {}
        for name, data in paths.items():
            p = self.output_dir / name
            p.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            written[name] = str(p)

        md = self._markdown(
            metrics=metrics,
            missing_ids=missing_ids,
            diagnostics=diagnostics,
            validation=validation,
            regression=regression,
            recommendation=recommendation,
            elapsed_s=elapsed_s,
            root_causes=dict(root_causes),
        )
        md_path = self.output_dir / "phase_r162_summary.md"
        md_path.write_text(md, encoding="utf-8")
        written["phase_r162_summary.md"] = str(md_path)
        return written

    @staticmethod
    def _markdown(
        metrics: ProjectCoverageMetrics,
        missing_ids: List[str],
        diagnostics: List[Dict[str, Any]],
        validation: Dict[str, Any],
        regression: Dict[str, Any],
        recommendation: str,
        elapsed_s: float,
        root_causes: Dict[str, int],
    ) -> str:
        sample = missing_ids[:20]
        more = len(missing_ids) - len(sample)
        sample_txt = ", ".join(sample) + (f" … (+{more} more)" if more > 0 else "")
        lines = [
            "# Phase R.1.6.2 — RULE-012 Mandatory Stirrup Coverage Validation",
            "",
            f"**MODEL_VERSION:** `{MODEL_VERSION}`",
            f"**Rule:** `{RULE_ID}` — Mandatory Stirrup Coverage Validation",
            f"**Elapsed:** `{elapsed_s:.2f}s`",
            "",
            "## Engineering Invariant",
            "",
            "Every beam shall contain at least one stirrup representation "
            "(Intent → Detail → Piece → EngineeringBar).",
            "",
            "Detection only — no automatic correction — no production modification.",
            "",
            "## Coverage Statistics",
            "",
            f"- Total beams: `{metrics.beam_count}`",
            f"- Detected stirrup families: `{metrics.detected_stirrup_families}`",
            f"- Coverage %: `{metrics.coverage_pct}`",
            f"- Pass %: `{metrics.pass_pct}`",
            f"- Fail %: `{metrics.fail_pct}`",
            f"- Missing %: `{metrics.missing_pct}`",
            "",
            "## Missing Stirrup Summary",
            "",
            f"- Missing beams: `{len(missing_ids)}`",
            f"- Sample IDs: {sample_txt or '(none)'}",
            f"- Diagnostics rows: `{len(diagnostics)}`",
            "",
            "## Root Cause / Phase Distribution",
            "",
        ]
        if root_causes:
            for phase, count in sorted(root_causes.items(), key=lambda x: (-x[1], x[0])):
                lines.append(f"- `{phase}`: `{count}`")
        else:
            lines.append("- (none)")
        lines.extend([
            "",
            "## Validation",
            "",
            f"- Passed: `{validation.get('passed')}/{validation.get('total')}`",
            f"- Overall: `{validation.get('overall_passed')}`",
            "",
            "## Regression",
            "",
            f"- Passed: `{regression.get('passed')}`",
            f"- Deterministic coverage: `{regression.get('deterministic_coverage')}`",
            "",
            "## Recommendation",
            "",
            (
                "**A)** Ready for Phase R.1.7 — Deterministic Engineering Correction Engine"
                if recommendation == "A"
                else "**B)** Resolve mandatory stirrup coverage failures before implementing "
                "deterministic corrections."
            ),
            "",
        ])
        return "\n".join(lines)
