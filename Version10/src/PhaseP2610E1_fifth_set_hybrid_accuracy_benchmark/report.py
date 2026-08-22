"""E.1 artefact writer. No production routing. No PNG copies."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import GATE_VERSION, LIVE_CLAUDE_CALL, MODEL_VERSION, PHASE_ID, PHASE_NAME, PRODUCTION_WRITE


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


def write_beam_review(*, out_root: Path, calc: Dict[str, Any], truth: Any, accuracy: Dict[str, Any]) -> None:
    folder = Path(out_root) / "review" / str(calc.get("beam_id"))
    hybrid = calc.get("hybrid_semantic") or {}
    _dump(folder / "hybrid_semantic_result.json", hybrid)
    _dump(folder / "semantic_provenance.json", hybrid.get("source_provenance") or {"kind": calc.get("provenance_kind")})
    _dump(folder / "engineering_bindings.json", calc.get("engineering_bindings") or {})
    _dump(
        folder / "engineering_calculation_summary.json",
        {
            "hybrid_weight_kg": calc.get("hybrid_weight_kg"),
            "status": calc.get("status"),
            "completeness": calc.get("completeness"),
            "spacer_weight_kg": calc.get("spacer_weight_kg"),
            "stirrup_weight_kg": calc.get("stirrup_weight_kg"),
            "group_counts": calc.get("group_counts"),
        },
    )
    _dump(folder / "benchmark_truth.json", truth if truth else {"source": "NONE", "available": False})
    _dump(folder / "beam_accuracy_metrics.json", accuracy)
    _dump(
        folder / "error_classifications.json",
        {
            "withheld": calc.get("withheld_ambiguous") or [],
            "status": calc.get("status"),
            "provenance_kind": calc.get("provenance_kind"),
        },
    )
    _dump(folder / "ambiguity_status.json", {"withheld": calc.get("withheld_ambiguous") or [], "status": calc.get("status")})


def write_validation_report(*, out_root: Path, result: Dict[str, Any]) -> None:
    k = result.get("kpis") or {}
    beam = k.get("beam_identification") or {}
    bar = k.get("bar_identification") or {}
    cor = k.get("correct_of_detected") or {}
    dia = k.get("diameter_identification") or {}
    steel = k.get("steel") or {}
    overall = k.get("overall") or {}
    vis = result.get("vision_coverage") or {}
    prov = result.get("provenance") or {}
    lines = [
        f"# {PHASE_ID} — {PHASE_NAME}",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        f"GATE: {GATE_VERSION}",
        f"DECISION: {result.get('decision')}",
        "",
        "Standalone Fifth Set benchmark of the **current hybrid architecture**.",
        "No historical comparison. No other drawing sets.",
        "",
        "Hybrid semantic authority: Claude Vision preferred after validation (D.1 contract).",
        "Deterministic engineering authority: geometry, cut length, development length, spacers, stirrup engineering, steel calculation.",
        "",
        f"- LIVE_CLAUDE_CALL = {LIVE_CLAUDE_CALL}",
        f"- PRODUCTION_WRITE = {PRODUCTION_WRITE}",
        f"- execution_mode = {result.get('mode')}",
        "",
        "## EXECUTIVE SUMMARY",
        "",
        f"| KPI | result |",
        f"|---|---:|",
        f"| Beam identification | {_fmt(beam.get('beam_identification_percent'))}% |",
        f"| Bar identification | {_fmt(bar.get('bar_identification_percent'))}% |",
        f"| Correct of detected bars | {_fmt(cor.get('correct_of_detected_percent'))}% |",
        f"| Diameter identification | {_fmt(dia.get('diameter_identification_percent'))}% |",
        f"| Steel accuracy | {_fmt(steel.get('weight_accuracy_percent'))}% |",
        f"| Overall accuracy | {_fmt(overall.get('overall_accuracy_percent'))}% |",
        "",
        f"- GT beams: {beam.get('total_ground_truth_beams')} · detected: {beam.get('detected_ground_truth_beams')}",
        f"- GT bars: {bar.get('total_ground_truth_bars')} · identified: {bar.get('identified_ground_truth_bars')} · MATCH: {cor.get('fully_matched_detected_bars')}",
        f"- Hybrid kg: {_fmt(steel.get('hybrid_total_kg'), 3)} · Benchmark kg: {_fmt(steel.get('benchmark_total_kg'), 3)} · abs error kg: {_fmt(steel.get('absolute_error_kg'), 3)}",
        "",
        "## 1. FIFTH SET PERFORMANCE",
        "",
        "| KPI | Raw calculation | Result |",
        "|---|---|---:|",
        f"| Beam identification | {beam.get('numerator')} / {beam.get('denominator')} × 100 | {_fmt(beam.get('beam_identification_percent'))}% |",
        f"| Bar identification | {bar.get('numerator')} / {bar.get('denominator')} × 100 | {_fmt(bar.get('bar_identification_percent'))}% |",
        f"| Correct of detected | {cor.get('numerator')} / {cor.get('denominator')} × 100 | {_fmt(cor.get('correct_of_detected_percent'))}% |",
        f"| Diameter identification | {dia.get('numerator')} / {dia.get('denominator')} × 100 | {_fmt(dia.get('diameter_identification_percent'))}% |",
        f"| Steel accuracy | `{steel.get('formula')}` | {_fmt(steel.get('weight_accuracy_percent'))}% |",
        f"| Overall accuracy | mean of four KPIs above excluding diameter | {_fmt(overall.get('overall_accuracy_percent'))}% |",
        "",
        "## 2. WHAT THE KPIs MEAN",
        "",
        "Beam identification: what share of estimator beams are present in the hybrid model.",
        "Bar identification: what share of estimator bars are paired to a model bar (QA.2A BarMatcher).",
        "Correct of detected: of paired bars, how many are full MATCH (role + diameter + quantity).",
        "Steel accuracy: QA.2A metric8 on total kg.",
        "Overall: mean of beam ID, bar ID, correct-of-detected, and steel accuracy.",
        "",
        "## 3. BAR INTERPRETATION PERFORMANCE",
        "",
        json.dumps(cor.get("taxonomy") or {}, indent=2),
        "",
        "## 4. DIAMETER PERFORMANCE",
        "",
        "| diameter | estimator kg | hybrid kg | difference kg | difference % |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in (result.get("diameter_wise") or {}).get("steel_rows") or []:
        lines.append(
            f"| {row.get('diameter_label')} | {_fmt(row.get('estimator_kg'), 3)} | {_fmt(row.get('model_kg'), 3)} | {_fmt(row.get('difference_kg'), 3)} | {_fmt(row.get('difference_pct'))} |"
        )
    sem = result.get("semantic_errors") or {}
    eng = result.get("engineering_errors") or {}
    lines += [
        "",
        "## 5. STEEL QUANTITY PERFORMANCE",
        "",
        f"- Hybrid total kg: {_fmt(steel.get('hybrid_total_kg'), 3)}",
        f"- Benchmark kg: {_fmt(steel.get('benchmark_total_kg'), 3)}",
        f"- Absolute difference kg: {_fmt(steel.get('absolute_error_kg'), 3)}",
        f"- Absolute error %: {_fmt(steel.get('absolute_error_percent'))}",
        f"- Steel accuracy %: {_fmt(steel.get('weight_accuracy_percent'))}",
        f"- Formula: `{steel.get('formula')}`",
        f"- Source: {steel.get('source')}",
        "",
        "## 6. HYBRID ARCHITECTURE ANALYSIS",
        "",
        "Vision preferred (after D.1 validation): target, layer, physical groups, bar count, diameter, specification, MAIN/EXTRA, support scope, stirrup identification.",
        "Deterministic: geometry, cut length, development length, hooks/bends, spacers, stirrup engineering, piece generation, weight.",
        f"Vision usable beams this run: {vis.get('usable_beam_count', 0)} (offline replay).",
        "",
        "## 7. ERROR BREAKDOWN",
        "",
        "Semantic interpretation errors:",
        json.dumps(sem.get("ranked") or [], indent=2),
        "",
        "Engineering calculation errors:",
        json.dumps(eng.get("ranked") or [], indent=2),
        "",
        "## 8. HYBRID PROVENANCE SUMMARY (coverage, not accuracy)",
        "",
        json.dumps(prov, indent=2, default=str),
        "",
        "## 9. CURRENT MODEL STATUS",
        "",
        "This is a benchmark of the current hybrid architecture on the Fifth Set only.",
        "It does not represent Second, Third, Fourth, or Sixth Sets, all-set generalization, or production readiness.",
        "No historical comparison is generated.",
        "",
        "## 10. METHODOLOGY AND LIMITATIONS",
        "",
        f"- truth source: {(result.get('truth') or {}).get('source')}",
        f"- mode: {result.get('mode')}",
        f"- vision usable: {vis.get('usable_beam_count')} scanned={vis.get('scanned')} api_failed={vis.get('api_failed')} other_set_skipped={vis.get('skipped_other_set')}",
        f"- withheld ambiguity groups: {prov.get('withheld_groups')}",
        f"- formulas: beam/bar = QA.2A matchers; steel = QA.2A metric8; overall = QA.2A/QA.3.0 four-KPI mean",
        "",
        f"- unit tests: {(result.get('unit_tests') or {}).get('passed')}/{(result.get('unit_tests') or {}).get('total')}",
        f"- fingerprints unchanged: {(result.get('fingerprints') or {}).get('unchanged')}",
        f"- production mutation: {(result.get('production') or {}).get('production_mutation_delta')}",
        "",
    ]
    (Path(out_root) / "validation_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> None:
    out_root = Path(out_root)
    k = result.get("kpis") or {}
    calcs = result.get("hybrid_calculations") or []
    bar_rows = ((k.get("bar_matching") or {}).get("rows") or [])
    beam_pairs = ((k.get("beam_matching") or {}).get("pairs") or [])
    truth_wb = (result.get("truth") or {}).get("workbook")
    truth_map = {}
    if truth_wb is not None:
        for b in getattr(truth_wb, "beams", []) or []:
            truth_map[b.beam_id] = {
                "beam_id": b.beam_id,
                "source": (result.get("truth") or {}).get("source"),
                "steel_kg": b.steel_kg,
                "bar_count": len(b.bars or []),
            }
    per_beam = []
    calc_by = {str(c.get("beam_id")): c for c in calcs}
    for p in beam_pairs:
        bid = p.get("estimator_beam_id") or p.get("model_beam_id")
        calc = calc_by.get(str(p.get("model_beam_id") or bid)) or {"beam_id": bid, "status": "MISSING_MODEL", "hybrid_weight_kg": None, "provenance_kind": "UNRESOLVED"}
        acc = {"pair": p, "hybrid_kg": calc.get("hybrid_weight_kg"), "status": calc.get("status")}
        per_beam.append({"beam_id": bid, **acc})
        write_beam_review(out_root=out_root, calc={**calc, "beam_id": calc.get("beam_id") or bid}, truth=truth_map.get(str(bid)), accuracy=acc)

    _dump(out_root / "fifth_set_population_manifest.json", result.get("population"))
    _dump(out_root / "hybrid_execution_manifest.json", result.get("execution_manifest"))
    _dump(out_root / "vision_coverage_report.json", result.get("vision_coverage"))
    _dump(out_root / "hybrid_beam_results.json", calcs)
    _dump(out_root / "hybrid_bar_results.json", bar_rows)
    _dump(out_root / "benchmark_truth_manifest.json", {kk: vv for kk, vv in (result.get("truth") or {}).items() if kk != "workbook"})
    _dump(out_root / "benchmark_mapping_audit.json", k.get("beam_matching"))
    _dump(out_root / "beam_identification_metrics.json", k.get("beam_identification"))
    _dump(out_root / "bar_identification_metrics.json", k.get("bar_identification"))
    _dump(out_root / "bar_matching_metrics.json", {kk: vv for kk, vv in (k.get("bar_matching") or {}).items() if kk != "rows"})
    _dump(out_root / "diameter_accuracy_report.json", k.get("diameter_identification"))
    _dump(out_root / "diameter_wise_performance.json", result.get("diameter_wise"))
    _dump(out_root / "steel_accuracy_metrics.json", k.get("steel"))
    _dump(out_root / "overall_accuracy_metrics.json", k.get("overall"))
    _dump(out_root / "hybrid_provenance_summary.json", result.get("provenance"))
    _dump(out_root / "semantic_error_analysis.json", result.get("semantic_errors"))
    _dump(out_root / "engineering_error_analysis.json", result.get("engineering_errors"))
    _dump(out_root / "stirrup_error_analysis.json", result.get("stirrup_errors"))
    _dump(out_root / "spacer_contribution_report.json", result.get("spacer_report"))
    _dump(out_root / "per_beam_accuracy.json", per_beam)
    _dump(out_root / "per_bar_accuracy.json", bar_rows)
    _dump(out_root / "error_taxonomy_summary.json", (k.get("correct_of_detected") or {}).get("taxonomy"))
    _dump(
        out_root / "accuracy_report_data.json",
        {
            "beam": k.get("beam_identification"),
            "bar": k.get("bar_identification"),
            "correct": k.get("correct_of_detected"),
            "diameter": k.get("diameter_identification"),
            "steel": k.get("steel"),
            "overall": k.get("overall"),
        },
    )
    _dump(
        out_root / "validation_summary.json",
        {
            "decision": result.get("decision"),
            "mode": result.get("mode"),
            "kpis": {
                "beam": (k.get("beam_identification") or {}).get("beam_identification_percent"),
                "bar": (k.get("bar_identification") or {}).get("bar_identification_percent"),
                "correct": (k.get("correct_of_detected") or {}).get("correct_of_detected_percent"),
                "diameter": (k.get("diameter_identification") or {}).get("diameter_identification_percent"),
                "steel": (k.get("steel") or {}).get("weight_accuracy_percent"),
                "overall": (k.get("overall") or {}).get("overall_accuracy_percent"),
            },
            "unit_tests": {kk: (result.get("unit_tests") or {}).get(kk) for kk in ("success", "passed", "total")},
        },
    )
    write_validation_report(out_root=out_root, result=result)
    slim = {
        kname: result.get(kname)
        for kname in (
            "phase_id",
            "phase_name",
            "model_version",
            "gate_version",
            "decision",
            "pass_fail",
            "mode",
            "live_claude_call",
            "runtime_s",
            "production",
        )
    }
    slim["kpis"] = {
        "beam_identification_percent": (k.get("beam_identification") or {}).get("beam_identification_percent"),
        "bar_identification_percent": (k.get("bar_identification") or {}).get("bar_identification_percent"),
        "correct_of_detected_percent": (k.get("correct_of_detected") or {}).get("correct_of_detected_percent"),
        "diameter_identification_percent": (k.get("diameter_identification") or {}).get("diameter_identification_percent"),
        "weight_accuracy_percent": (k.get("steel") or {}).get("weight_accuracy_percent"),
        "overall_accuracy_percent": (k.get("overall") or {}).get("overall_accuracy_percent"),
        "hybrid_total_kg": (k.get("steel") or {}).get("hybrid_total_kg"),
        "benchmark_total_kg": (k.get("steel") or {}).get("benchmark_total_kg"),
    }
    slim["vision_coverage"] = {
        "usable_beam_count": (result.get("vision_coverage") or {}).get("usable_beam_count"),
        "scanned": (result.get("vision_coverage") or {}).get("scanned"),
        "api_failed": (result.get("vision_coverage") or {}).get("api_failed"),
    }
    slim["unit_tests"] = {kk: (result.get("unit_tests") or {}).get(kk) for kk in ("success", "passed", "total")}
    slim["fingerprints"] = {"unchanged": (result.get("fingerprints") or {}).get("unchanged"), "changed_keys": (result.get("fingerprints") or {}).get("changed_keys")}
    slim["pdf_path"] = result.get("pdf_path")
    _dump(out_root / "P2.6.10-E.1_RESULTS.json", slim)


__all__ = ["write_reports"]
