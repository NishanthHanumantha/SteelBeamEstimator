"""D.4 shadow reports. No production routing. No PNG copies."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import GATE_VERSION, LIVE_CLAUDE_CALL, MODEL_VERSION, PHASE_ID, PHASE_NAME, PRODUCTION_WRITE


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _fmt(v: Any, n: int = 3) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.{n}f}"
    except (TypeError, ValueError):
        return str(v)


def write_beam_review(*, out_root: Path, bound: Dict[str, Any], calc: Dict[str, Any], comparison: Dict[str, Any], contribution: Dict[str, Any], truth: Any, baseline: Any) -> None:
    folder = Path(out_root) / "review" / str(calc.get("beam_id"))
    _dump(
        folder / "hybrid_semantic_summary.json",
        {
            "beam_id": calc.get("beam_id"),
            "groups": [
                {
                    "group_id": g.get("group_id"),
                    "origin": g.get("origin"),
                    "layer": (g.get("semantic") or {}).get("layer"),
                    "role": g.get("role"),
                    "diameter": g.get("diameter_mm"),
                    "bar_count": g.get("bar_count"),
                    "ambiguous": g.get("ambiguous"),
                }
                for g in calc.get("groups") or []
            ],
        },
    )
    _dump(folder / "engineering_bindings.json", bound)
    _dump(folder / "hybrid_calculation.json", calc)
    _dump(folder / "deterministic_baseline.json", baseline)
    _dump(folder / "benchmark_truth.json", truth if truth else {"source": "NONE", "available": False})
    _dump(folder / "accuracy_comparison.json", comparison)
    _dump(folder / "field_provenance.json", [g.get("semantic") for g in calc.get("groups") or []])
    _dump(folder / "vision_contribution.json", contribution)


def write_validation_report(*, out_root: Path, result: Dict[str, Any]) -> None:
    popm = result.get("population_metrics") or {}
    comps = result.get("comparisons") or []
    dia = (result.get("diameter_report") or {}).get("rows") or []
    contrib = result.get("contribution_summary") or {}
    amb = result.get("ambiguous_report") or []
    statuses = popm.get("calculation_completeness") or {}
    lines = [
        f"# {PHASE_ID} — {PHASE_NAME}",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        f"GATE: {GATE_VERSION}",
        f"DECISION: {result.get('decision')}",
        "",
        "SHADOW ONLY. Hybrid engineering calculation versus frozen deterministic baseline and estimator truth.",
        "Weight formula: `W = (pi * d^2 / 4) * L * qty * 7850 / 1e9` (PieceGeometry / V.B.1).",
        "Error formula: `abs(predicted - benchmark) / benchmark * 100` (QA.2A metric8 / P258).",
        "Accuracy formula: `max(0, 100 - weight_error_percent)`.",
        "Accuracy improvement delta = hybrid_accuracy_pct − deterministic_accuracy_pct (percentage points).",
        "Do not treat ENGINEERING_BINDING_COVERAGE as accuracy. This phase reports steel-weight accuracy only where benchmark truth exists.",
        "",
        f"- LIVE_CLAUDE_CALL = {LIVE_CLAUDE_CALL}",
        f"- PRODUCTION_WRITE = {PRODUCTION_WRITE}",
        "",
        "## TABLE A — POPULATION",
        "",
        f"| metric | count |",
        f"|---|---|",
        f"| total discovered | {popm.get('population_discovered')} |",
        f"| SHADOW_COMPLETE | {statuses.get('SHADOW_COMPLETE', 0)} |",
        f"| SHADOW_PARTIAL | {statuses.get('SHADOW_PARTIAL', 0)} |",
        f"| SHADOW_AMBIGUOUS | {statuses.get('SHADOW_AMBIGUOUS', 0)} |",
        f"| SHADOW_INCOMPATIBLE | {statuses.get('SHADOW_INCOMPATIBLE', 0)} |",
        f"| NO_BENCHMARK_TRUTH | {popm.get('no_benchmark_truth')} |",
        "",
        "## TABLE B — WEIGHT COMPARISON",
        "",
        "| beam | hybrid kg | deterministic kg | benchmark kg | hybrid error % | deterministic error % | winner |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for c in comps:
        lines.append(
            f"| {c.get('beam_id')} | {_fmt(c.get('hybrid_kg'))} | {_fmt(c.get('deterministic_kg'))} | {_fmt(c.get('benchmark_kg'))} | {_fmt(c.get('hybrid_error_pct'))} | {_fmt(c.get('deterministic_error_pct'))} | {c.get('winner')} |"
        )
    lines += [
        "",
        "## TABLE C — POPULATION TOTALS (beams with benchmark truth only)",
        "",
        f"| metric | value |",
        f"|---|---|",
        f"| hybrid total kg | {_fmt(popm.get('hybrid_total_kg'))} |",
        f"| deterministic total kg | {_fmt(popm.get('deterministic_total_kg'))} |",
        f"| benchmark total kg | {_fmt(popm.get('benchmark_total_kg'))} |",
        f"| hybrid absolute error kg | {_fmt(popm.get('hybrid_absolute_error_kg'))} |",
        f"| deterministic absolute error kg | {_fmt(popm.get('deterministic_absolute_error_kg'))} |",
        f"| hybrid error % | {_fmt(popm.get('hybrid_error_pct'))} |",
        f"| deterministic error % | {_fmt(popm.get('deterministic_error_pct'))} |",
        f"| hybrid accuracy % | {_fmt(popm.get('hybrid_accuracy_pct'))} |",
        f"| deterministic accuracy % | {_fmt(popm.get('deterministic_accuracy_pct'))} |",
        f"| accuracy improvement delta (pp) | {_fmt(popm.get('accuracy_improvement_delta_pp'))} |",
        "",
        "## TABLE D — DIAMETER PERFORMANCE",
        "",
        "| diameter | hybrid predicted kg | deterministic predicted kg | benchmark kg | hybrid error % | deterministic error % |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in dia:
        lines.append(
            f"| {r.get('diameter')} | {_fmt(r.get('hybrid_predicted_kg'))} | {_fmt(r.get('deterministic_predicted_kg'))} | {_fmt(r.get('benchmark_kg'))} | {_fmt(r.get('hybrid_error_pct'))} | {_fmt(r.get('deterministic_error_pct'))} |"
        )
    lines += [
        "",
        "## TABLE E — CONTRIBUTION ANALYSIS",
        "",
        "| category | count |",
        "|---|---:|",
        f"| hybrid improvements | {contrib.get('improvements', 0)} |",
        f"| hybrid regressions | {contrib.get('regressions', 0)} |",
        f"| ambiguous withheld beams | {contrib.get('ambiguous_withheld_beams', 0)} |",
    ]
    for k, v in sorted((contrib.get("code_counts") or {}).items()):
        lines.append(f"| {k} | {v} |")
    lines += [
        "",
        f"outcomes: `{json.dumps(contrib.get('outcomes') or {}, default=str)}`",
        "",
        "## TABLE F — AMBIGUITY",
        "",
        "| beam | group | reason | calculated | completeness impact |",
        "|---|---|---|---|---|",
    ]
    if not amb:
        lines.append("| — | — | none | — | — |")
    for a in amb:
        lines.append(
            f"| {a.get('beam_id')} | {a.get('group_id')} | {a.get('reason')} | {a.get('calculated')} | withheld from beam total |"
        )
    unit = result.get("unit_tests") or {}
    anti = result.get("anti_hardcoding") or {}
    fp = result.get("fingerprints") or {}
    lines += [
        "",
        "## Tests / firewall",
        "",
        f"- D.4 unit tests: {unit.get('passed')}/{unit.get('total')} success={unit.get('success')}",
        f"- anti-hardcoding: {anti.get('ok')}",
        f"- fingerprints unchanged: {fp.get('unchanged')}",
        f"- production mutation: {(result.get('production') or {}).get('production_mutation_delta')}",
        "",
        "No production interpretation change. No R1.3 / SI / steel / BBS / workbook mutation.",
        "",
    ]
    (Path(out_root) / "validation_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> None:
    out_root = Path(out_root)
    bound = result.get("bindings") or []
    calcs = result.get("hybrid_calculations") or []
    comps = result.get("comparisons") or []
    contribs = result.get("contributions") or []
    truth_by = ((result.get("truth") or {}).get("by_id") or {})
    base_by = ((result.get("baseline") or {}).get("by_id") or {})
    bound_by = {str(b.get("beam_id")): b for b in bound}
    contrib_by = {str(c.get("beam_id")): c for c in contribs}
    for calc in calcs:
        bid = str(calc.get("beam_id"))
        write_beam_review(
            out_root=out_root,
            bound=bound_by.get(bid) or {},
            calc=calc,
            comparison=next((c for c in comps if c.get("beam_id") == bid), {}),
            contribution=contrib_by.get(bid) or {},
            truth=truth_by.get(bid),
            baseline=base_by.get(bid),
        )
    _dump(out_root / "benchmark_population_manifest.json", result.get("population"))
    _dump(out_root / "hybrid_engineering_calculations.json", calcs)
    _dump(out_root / "hybrid_beam_results.json", calcs)
    _dump(out_root / "deterministic_baseline_comparison.json", result.get("baseline"))
    _dump(out_root / "benchmark_truth_manifest.json", result.get("truth"))
    _dump(out_root / "accuracy_metrics.json", result.get("population_metrics"))
    _dump(out_root / "diameter_accuracy_report.json", result.get("diameter_report"))
    _dump(out_root / "vision_contribution_analysis.json", {"beams": contribs, "summary": result.get("contribution_summary")})
    _dump(out_root / "ambiguous_calculation_report.json", result.get("ambiguous_report"))
    _dump(out_root / "stirrup_engineering_report.json", [c.get("stirrups") for c in calcs])
    _dump(out_root / "spacer_contribution_report.json", [c.get("spacers") for c in calcs])
    _dump(out_root / "per_beam_comparison.json", comps)
    _dump(out_root / "population_accuracy_summary.json", result.get("population_metrics"))
    _dump(out_root / "resolution_provenance_audit.json", result.get("provenance_audit"))
    _dump(out_root / "anti_hardcoding_results.json", result.get("anti_hardcoding"))
    _dump(out_root / "source_fingerprint_check.json", result.get("fingerprints"))
    _dump(out_root / "production_mutation_check.json", result.get("production"))
    _dump(
        out_root / "validation_summary.json",
        {
            "decision": result.get("decision"),
            "population_metrics": result.get("population_metrics"),
            "authority": result.get("provenance_audit"),
            "unit_tests": {k: (result.get("unit_tests") or {}).get(k) for k in ("success", "passed", "total")},
        },
    )
    write_validation_report(out_root=out_root, result=result)
    slim = {
        k: result.get(k)
        for k in (
            "phase_id",
            "phase_name",
            "model_version",
            "gate_version",
            "decision",
            "pass_fail",
            "population_metrics",
            "production",
            "fingerprints",
            "unit_tests",
            "live_claude_call",
            "runtime_s",
            "recommendation",
        )
    }
    if isinstance(slim.get("unit_tests"), dict):
        slim["unit_tests"] = {k: slim["unit_tests"].get(k) for k in ("success", "passed", "total")}
    fp = slim.get("fingerprints")
    if isinstance(fp, dict):
        slim["fingerprints"] = {"unchanged": fp.get("unchanged"), "changed_keys": fp.get("changed_keys")}
    _dump(out_root / "P2.6.10-D.4_RESULTS.json", slim)


__all__ = ["write_beam_review", "write_reports"]
