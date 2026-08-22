"""E.2 artefact writer. Additive namespace only. No PNG copies. No production routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import GATE_VERSION, MODEL_VERSION, PHASE_ID, PHASE_NAME, PRODUCTION_WRITE


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _fmt(v: Any, n: int = 2) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.{n}f}"
    except (TypeError, ValueError):
        return str(v)


def _kpi_block(k: Dict[str, Any]) -> Dict[str, Any]:
    if not k:
        return {}
    return {
        "beam_identification_percent": (k.get("beam_identification") or {}).get("beam_identification_percent"),
        "bar_identification_percent": (k.get("bar_identification") or {}).get("bar_identification_percent"),
        "correct_of_detected_percent": (k.get("correct_of_detected") or {}).get("correct_of_detected_percent"),
        "diameter_identification_percent": (k.get("diameter_identification") or {}).get("diameter_identification_percent"),
        "weight_accuracy_percent": (k.get("steel") or {}).get("weight_accuracy_percent"),
        "overall_accuracy_percent": (k.get("overall") or {}).get("overall_accuracy_percent"),
        "hybrid_total_kg": (k.get("steel") or {}).get("hybrid_total_kg"),
        "benchmark_total_kg": (k.get("steel") or {}).get("benchmark_total_kg"),
        "absolute_error_kg": (k.get("steel") or {}).get("absolute_error_kg"),
        "signed_error_kg": (k.get("steel") or {}).get("signed_error_kg"),
        "beam_n": (k.get("beam_identification") or {}).get("numerator"),
        "beam_d": (k.get("beam_identification") or {}).get("denominator"),
        "bar_n": (k.get("bar_identification") or {}).get("numerator"),
        "bar_d": (k.get("bar_identification") or {}).get("denominator"),
        "correct_n": (k.get("correct_of_detected") or {}).get("numerator"),
        "correct_d": (k.get("correct_of_detected") or {}).get("denominator"),
        "taxonomy": (k.get("correct_of_detected") or {}).get("taxonomy"),
    }


def write_beam_review(*, out_root: Path, calc: Dict[str, Any], truth: Any, accuracy: Dict[str, Any]) -> None:
    folder = Path(out_root) / "review" / str(calc.get("beam_id"))
    live = calc.get("live") or {}
    _dump(folder / "visual_source_provenance.json", live.get("visual") or {})
    _dump(folder / "vision_result.json", {k: (calc.get("live_full") or {}).get(k) for k in ("call_provenance", "semantic_usable", "failure_category", "api_success", "schema_valid", "model")})
    _dump(folder / "deterministic_result.json", {"beam_id": calc.get("beam_id"), "spacers": calc.get("spacers"), "stirrups_engineering": (calc.get("stirrups") or {}).get("reason")})
    _dump(folder / "hybrid_result.json", calc.get("hybrid_semantic") or {})
    _dump(folder / "provenance_summary.json", {"kind": calc.get("provenance_kind"), "vision_used": calc.get("vision_used"), "call_provenance": live.get("call_provenance")})
    _dump(folder / "semantic_comparison.json", accuracy)
    _dump(folder / "engineering_status.json", {"status": calc.get("status"), "hybrid_weight_kg": calc.get("hybrid_weight_kg")})
    _dump(folder / "benchmark_match_summary.json", truth if truth else {"available": False})


def write_validation_report(*, out_root: Path, result: Dict[str, Any]) -> None:
    splits = result.get("splits") or {}
    full_k = ((splits.get("FULL_POPULATION") or {}).get("kpis") or {})
    hy_k = ((splits.get("HYBRID_ONLY") or {}).get("kpis") or {})
    fb_k = ((splits.get("FALLBACK_ONLY") or {}).get("kpis") or {})
    vis = result.get("vision_coverage") or {}
    live = result.get("live_summary") or {}
    lines = [
        f"# {PHASE_ID} — {PHASE_NAME}",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        f"GATE: {GATE_VERSION}",
        f"DECISION: {result.get('decision')}",
        f"LIVE_COMPLETION: {result.get('live_completion')}",
        f"MODE: {result.get('mode')}",
        "",
        "Standalone Fifth Set live-Vision hybrid benchmark. No historical comparison.",
        f"PRODUCTION_WRITE = {PRODUCTION_WRITE}",
        "",
        "## 1. MODEL VERSION",
        MODEL_VERSION,
        "",
        "## 2. GATE",
        GATE_VERSION,
        "",
        "## 3. FINAL DECISION",
        str(result.get("decision")),
        str(result.get("live_completion")),
        "",
        "## 4. POPULATION DISCOVERY",
        json.dumps({k: (result.get("population") or {}).get(k) for k in ("discovered_model_beam_count", "discovered_estimator_beam_count", "matched_benchmark_population", "discovery_method")}, indent=2),
        "",
        "## 5. VISION COVERAGE",
        json.dumps(vis, indent=2, default=str),
        "",
        "## 6. EXECUTION PROVENANCE",
        json.dumps(result.get("execution_provenance") or {}, indent=2),
        "",
        "## 7–13. ACCURACY (HYBRID / FALLBACK / FULL)",
        "",
        "| cohort | beam % | bar % | correct % | diameter % | steel % | overall % | kg model | kg bench |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, block in (("HYBRID_ONLY", hy_k), ("FALLBACK_ONLY", fb_k), ("FULL_POPULATION", full_k)):
        b = _kpi_block(block)
        lines.append(
            f"| {name} | {_fmt(b.get('beam_identification_percent'))} | {_fmt(b.get('bar_identification_percent'))} | {_fmt(b.get('correct_of_detected_percent'))} | {_fmt(b.get('diameter_identification_percent'))} | {_fmt(b.get('weight_accuracy_percent'))} | {_fmt(b.get('overall_accuracy_percent'))} | {_fmt(b.get('hybrid_total_kg'), 3)} | {_fmt(b.get('benchmark_total_kg'), 3)} |"
        )
    lines += [
        "",
        "## 14. SEMANTIC ERROR TAXONOMY",
        json.dumps(result.get("error_taxonomy") or {}, indent=2),
        "",
        "## 15. ENGINEERING ERROR SUMMARY",
        json.dumps(result.get("engineering_errors") or {}, indent=2, default=str),
        "",
        "## 16. STIRRUP PERFORMANCE",
        json.dumps(result.get("stirrup_errors") or {}, indent=2, default=str),
        "",
        "## 17. SPACER CONTRIBUTION",
        json.dumps(result.get("spacer_report") or {}, indent=2),
        "",
        "## 18. HYBRID PROVENANCE (coverage, not accuracy)",
        json.dumps(result.get("provenance") or {}, indent=2),
        "",
        "## 19. AMBIGUOUS / WITHHELD",
        json.dumps({"withheld_groups": (result.get("provenance") or {}).get("withheld_groups"), "forced_resolutions": 0}, indent=2),
        "",
        "## 20. VISION FAILURE ANALYSIS",
        json.dumps(result.get("vision_failures") or {}, indent=2),
        "",
        "## 21. COST / EXECUTION",
        json.dumps(live, indent=2, default=str),
        "",
        "## 22. METHODOLOGY",
        "QA.2A BeamMatcher, BarMatcher, MetricsEngine metric8, QA.3.0 four-KPI overall mean. Diameter excluded from overall.",
        "Ground truth source: ESTIMATOR_EXCEL. Workbook mapping may not perfectly represent physical drawing interpretation.",
        "",
        "## 27. LIMITATIONS",
        json.dumps(result.get("limitations") or [], indent=2),
        "",
        "## 28. CONCLUSION",
        str(result.get("conclusion") or ""),
        "",
    ]
    (Path(out_root) / "validation_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> None:
    out_root = Path(out_root)
    splits = result.get("splits") or {}
    full_k = ((splits.get("FULL_POPULATION") or {}).get("kpis") or {})
    calcs = result.get("hybrid_calculations") or []
    pop = result.get("population") or {}
    truth_wb = (pop.get("truth") or {}).get("workbook")
    truth_map = {}
    if truth_wb is not None:
        for b in getattr(truth_wb, "beams", []) or []:
            truth_map[b.beam_id] = {"beam_id": b.beam_id, "steel_kg": b.steel_kg, "bar_count": len(b.bars or [])}
    slim_calcs = []
    for c in calcs:
        slim_calcs.append(
            {
                "beam_id": c.get("beam_id"),
                "provenance_kind": c.get("provenance_kind"),
                "vision_used": c.get("vision_used"),
                "hybrid_weight_kg": c.get("hybrid_weight_kg"),
                "status": c.get("status"),
                "live": c.get("live"),
            }
        )
        write_beam_review(
            out_root=out_root,
            calc=c,
            truth=truth_map.get(str(c.get("beam_id"))),
            accuracy={"kind": c.get("provenance_kind"), "kg": c.get("hybrid_weight_kg")},
        )
    pop_out = {k: v for k, v in pop.items() if k not in ("catalog", "truth", "population")}
    _dump(out_root / "benchmark_population_manifest.json", pop_out)
    _dump(out_root / "visual_source_manifest.json", result.get("visual_sources"))
    _dump(out_root / "vision_eligibility_manifest.json", result.get("eligibility_counts"))
    _dump(out_root / "live_execution_manifest.json", result.get("live_execution"))
    _dump(out_root / "vision_live_results.json", [c.get("live") for c in calcs])
    _dump(out_root / "vision_failure_analysis.json", result.get("vision_failures"))
    _dump(out_root / "hybrid_semantic_results.json", [c.get("hybrid_semantic") for c in calcs])
    _dump(out_root / "hybrid_engineering_bindings.json", [c.get("engineering_bindings") for c in calcs])
    _dump(out_root / "hybrid_calculation_results.json", slim_calcs)
    _dump(out_root / "hybrid_provenance_summary.json", result.get("provenance"))
    _dump(out_root / "hybrid_fallback_comparison.json", result.get("execution_provenance"))
    _dump(out_root / "semantic_accuracy_summary.json", result.get("semantic_fields"))
    _dump(out_root / "engineering_accuracy_summary.json", result.get("engineering_errors"))
    _dump(out_root / "stirrup_performance_summary.json", result.get("stirrup_errors"))
    _dump(out_root / "spacer_contribution_summary.json", result.get("spacer_report"))
    _dump(
        out_root / "accuracy_metrics.json",
        {
            "HYBRID_ONLY": _kpi_block(((splits.get("HYBRID_ONLY") or {}).get("kpis") or {})),
            "FALLBACK_ONLY": _kpi_block(((splits.get("FALLBACK_ONLY") or {}).get("kpis") or {})),
            "FULL_POPULATION": _kpi_block(full_k),
        },
    )
    _dump(out_root / "error_taxonomy.json", result.get("error_taxonomy"))
    _dump(
        out_root / "benchmark_methodology.json",
        {
            "ground_truth_source": "ESTIMATOR_EXCEL",
            "beam": "PhaseQA.2A_ground_truth_benchmark.beam_matcher.BeamMatcher",
            "bar": "PhaseQA.2A_ground_truth_benchmark.bar_matcher.BarMatcher",
            "steel": "QA.2A metric8 max(0, 100 - abs(model-bench)/bench*100)",
            "overall": "mean(beam ID, bar ID, correct-of-detected, steel); diameter excluded",
            "limitation": "Estimator workbook comparison is benchmark truth; row-level mapping may not perfectly represent physical drawing interpretation.",
        },
    )
    _dump(out_root / "resolution_audit.json", result.get("anti_hardcoding"))
    _dump(
        out_root / "accuracy_report_data.json",
        {
            "hybrid": _kpi_block(((splits.get("HYBRID_ONLY") or {}).get("kpis") or {})),
            "fallback": _kpi_block(((splits.get("FALLBACK_ONLY") or {}).get("kpis") or {})),
            "full": _kpi_block(full_k),
            "applicable": {
                "HYBRID_ONLY": (splits.get("HYBRID_ONLY") or {}).get("applicable"),
                "FALLBACK_ONLY": (splits.get("FALLBACK_ONLY") or {}).get("applicable"),
                "FULL_POPULATION": (splits.get("FULL_POPULATION") or {}).get("applicable"),
            },
        },
    )
    write_validation_report(out_root=out_root, result=result)
    slim = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "decision": result.get("decision"),
        "live_completion": result.get("live_completion"),
        "pass_fail": result.get("pass_fail"),
        "mode": result.get("mode"),
        "live_claude_call": result.get("live_claude_call"),
        "runtime_s": result.get("runtime_s"),
        "production": result.get("production"),
        "kpis": _kpi_block(full_k),
        "splits": {n: _kpi_block(((splits.get(n) or {}).get("kpis") or {})) for n in ("HYBRID_ONLY", "FALLBACK_ONLY", "FULL_POPULATION")},
        "execution_provenance": result.get("execution_provenance"),
        "vision_coverage": result.get("vision_coverage"),
        "live_summary": result.get("live_summary"),
        "unit_tests": {kk: (result.get("unit_tests") or {}).get(kk) for kk in ("success", "passed", "total")},
        "fingerprints": {"unchanged": (result.get("fingerprints") or {}).get("unchanged"), "changed_keys": (result.get("fingerprints") or {}).get("changed_keys")},
        "prior_phase_unit_ok": {k: {"ok": (v or {}).get("ok"), "passed": (v or {}).get("passed")} for k, v in (result.get("prior_phase_unit_ok") or {}).items()},
        "limitations": result.get("limitations"),
        "conclusion": result.get("conclusion"),
        "pdf_path": result.get("pdf_path"),
    }
    _dump(out_root / "P2.6.10-E.2_RESULTS.json", slim)


__all__ = ["write_reports"]
