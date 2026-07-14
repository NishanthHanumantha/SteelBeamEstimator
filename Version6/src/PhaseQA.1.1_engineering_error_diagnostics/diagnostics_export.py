"""
Phase QA.1.1 — Module 14: Diagnostics Export
Export 12 JSON reports to the output directory.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import asdict
from typing import Any, Dict, List

from diagnostic_models import EngineeringDiagnostic, PriorityFix


def _base() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve()
    return here.parents[2]   # Version6/


def _out_dir() -> pathlib.Path:
    d = _base() / "data" / "output" / "PhaseQA.1.1_engineering_error_diagnostics"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write(path: pathlib.Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _diag_dict(d: EngineeringDiagnostic) -> Dict[str, Any]:
    return {
        "diagnostic_id":     d.diagnostic_id,
        "drawing_name":      d.drawing_name,
        "beam_id":           d.beam_id,
        "bar_id":            d.bar_id,
        "error_type":        d.error_type,
        "expected_value":    d.expected_value,
        "predicted_value":   d.predicted_value,
        "difference":        d.difference,
        "pipeline_stage":    d.pipeline_stage,
        "root_cause":        d.root_cause,
        "severity":          d.severity,
        "impact_score":      d.impact_score,
        "impact_level":      d.impact_level,
        "confidence":        d.confidence,
        "downstream_modules": d.downstream_modules,
        "recommended_fix":   d.recommended_fix,
        "priority_score":    d.priority_score,
        "priority_rank":     d.priority_rank,
        "engineering_notes": d.engineering_notes,
        "traceability":      d.traceability,
    }


class DiagnosticsExport:
    """Exports all 12 diagnostic artefacts."""

    def export_all(
        self,
        diagnostics: List[EngineeringDiagnostic],
        priority_fixes: List[PriorityFix],
        full_report: Dict[str, Any],
        stats: Dict[str, Any],
        benchmark_id: str,
        model_version: str,
        timestamp: str,
    ) -> Dict[str, str]:
        out = _out_dir()
        meta = {"model_version": model_version, "benchmark_id": benchmark_id, "timestamp": timestamp}
        paths: Dict[str, str] = {}

        def wp(name: str, data: Any) -> None:
            p = out / name
            _write(p, data)
            paths[name] = str(p)

        # 1. Full diagnostics report
        wp("engineering_diagnostics_report.json", {**meta, **full_report})

        # 2. Summary
        wp("engineering_diagnostics_summary.json", {
            **meta,
            "total_diagnostics": len(diagnostics),
            "root_cause_distribution": stats.get("root_cause_distribution", {}),
            "pipeline_stage_distribution": stats.get("pipeline_stage_distribution", {}),
            "severity_distribution": stats.get("severity_distribution", {}),
            "impact_distribution": stats.get("impact_distribution", {}),
            "average_confidence": stats.get("average_confidence", 0.0),
            "average_impact_score": stats.get("average_impact_score", 0.0),
        })

        # 3. Root cause analysis
        wp("root_cause_analysis.json", {
            **meta,
            "root_causes": [
                {
                    "root_cause": rc,
                    "count": cnt,
                    "diagnostics": [
                        _diag_dict(d) for d in diagnostics if d.root_cause == rc
                    ],
                }
                for rc, cnt in stats.get("root_cause_distribution", {}).items()
            ],
        })

        # 4. Pipeline stage analysis
        wp("pipeline_stage_analysis.json", {
            **meta,
            "stages": [
                {
                    "stage": st,
                    "count": cnt,
                    "diagnostics": [
                        _diag_dict(d) for d in diagnostics if d.pipeline_stage == st
                    ],
                }
                for st, cnt in stats.get("pipeline_stage_distribution", {}).items()
            ],
        })

        # 5. Impact assessment
        wp("impact_assessment.json", {
            **meta,
            "impact_distribution": stats.get("impact_distribution", {}),
            "severity_distribution": stats.get("severity_distribution", {}),
            "critical_diagnostics": [
                _diag_dict(d) for d in diagnostics if d.impact_level == "CRITICAL"
            ],
            "high_diagnostics": [
                _diag_dict(d) for d in diagnostics if d.impact_level == "HIGH"
            ],
            "medium_diagnostics": [
                _diag_dict(d) for d in diagnostics if d.impact_level == "MEDIUM"
            ],
            "low_diagnostics": [
                _diag_dict(d) for d in diagnostics if d.impact_level == "LOW"
            ],
        })

        # 6. Engineering recommendations
        seen: Dict[str, str] = {}
        for d in diagnostics:
            if d.root_cause not in seen:
                seen[d.root_cause] = d.recommended_fix
        wp("engineering_recommendations.json", {
            **meta,
            "recommendations": [
                {"root_cause": rc, "recommendation": rec}
                for rc, rec in seen.items()
            ],
        })

        # 7. Diagnostic statistics
        wp("diagnostic_statistics.json", {**meta, **stats})

        # 8. Priority fix list
        wp("priority_fix_list.json", {
            **meta,
            "total_fixes": len(priority_fixes),
            "fixes": [
                {
                    "rank": f.rank,
                    "fix_title": f.fix_title,
                    "error_type": f.error_type,
                    "root_cause": f.root_cause,
                    "pipeline_stage": f.pipeline_stage,
                    "frequency": f.frequency,
                    "severity": f.severity,
                    "priority_score": f.priority_score,
                    "expected_improvement_pct": f.expected_improvement_pct,
                    "kpi_affected": f.kpi_affected,
                    "recommendation": f.recommendation,
                    "affected_beams": f.affected_beams,
                }
                for f in priority_fixes
            ],
        })

        # 9–12: Subset exports by category
        def _subset(prefix: str) -> List[Dict]:
            return [_diag_dict(d) for d in diagnostics
                    if prefix in d.diagnostic_id or prefix.lower() in d.error_type.lower()]

        wp("beam_diagnostics.json", {
            **meta,
            "diagnostics": [_diag_dict(d) for d in diagnostics if "BEAM" in d.diagnostic_id],
        })
        wp("feature_diagnostics.json", {
            **meta,
            "diagnostics": [_diag_dict(d) for d in diagnostics if "FEAT" in d.diagnostic_id],
        })
        wp("pattern_diagnostics.json", {
            **meta,
            "diagnostics": [_diag_dict(d) for d in diagnostics if "PATTERN" in d.diagnostic_id],
        })
        wp("bbs_diagnostics.json", {
            **meta,
            "diagnostics": [_diag_dict(d) for d in diagnostics if "BBS" in d.diagnostic_id],
        })

        return paths
