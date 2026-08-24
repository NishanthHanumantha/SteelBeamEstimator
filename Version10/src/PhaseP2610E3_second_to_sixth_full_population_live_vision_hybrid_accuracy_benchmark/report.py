"""E.3 artefact writer. Additive namespace only. No production routing. No QA.30 overwrite."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .charts import write_charts
from .config import (
    DOCX_NAME,
    GATE_VERSION,
    INCLUDED_SET_KEYS,
    MODEL_VERSION,
    PDF_NAME,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_WRITE,
)
from .docx_report import write_docx
from .metrics import pool_identification_rows, pool_steel_rows
from .pdf_report import write_pdf
from .pooling import display_block, merge_taxonomy, pool_kpi_blocks
from .population import slim_set_population


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


def write_beam_review(*, out_root: Path, set_key: str, calc: Dict[str, Any], truth: Any) -> None:
    folder = Path(out_root) / "review" / str(set_key) / str(calc.get("beam_id"))
    live = calc.get("live") or {}
    _dump(folder / "visual_source_provenance.json", live.get("visual") or {})
    _dump(
        folder / "vision_result.json",
        {
            k: (calc.get("live_full") or {}).get(k)
            for k in ("call_provenance", "semantic_usable", "failure_category", "api_success", "schema_valid", "model")
        },
    )
    _dump(folder / "hybrid_result.json", calc.get("hybrid_semantic") or {})
    _dump(
        folder / "provenance_summary.json",
        {
            "kind": calc.get("provenance_kind"),
            "vision_used": calc.get("vision_used"),
            "call_provenance": live.get("call_provenance"),
            "set_key": set_key,
        },
    )
    _dump(folder / "engineering_status.json", {"status": calc.get("status"), "hybrid_weight_kg": calc.get("hybrid_weight_kg")})
    _dump(folder / "benchmark_match_summary.json", truth if truth else {"available": False})


def _md_table(headers: List[str], rows: List[List[str]]) -> List[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return lines


def write_validation_report(*, out_root: Path, result: Dict[str, Any], report_data: Dict[str, Any]) -> None:
    pop = report_data.get("population") or {}
    vis = report_data.get("vision_execution") or {}
    per_set = report_data.get("per_set") or {}
    pooled = report_data.get("pooled") or {}
    tax = report_data.get("semantic_taxonomy_pooled") or {}
    eng = (report_data.get("engineering_errors") or {}).get("counts") or {}
    cost = report_data.get("cost") or {}
    prod = result.get("production") or {}
    lines = [
        f"# {PHASE_ID} — {PHASE_NAME}",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        f"GATE: {GATE_VERSION}",
        f"DECISION: {result.get('decision')}",
        f"MODE: {result.get('mode')}",
        f"PRODUCTION_WRITE = {PRODUCTION_WRITE}",
        "",
        "## TABLE A — POPULATION BY SET",
        "",
    ]
    rows_a = []
    for key in INCLUDED_SET_KEYS:
        p = (pop.get("by_set") or {}).get(key) or {}
        s = per_set.get(key) or {}
        um = p.get("unmatched_model_beams") or []
        ug = p.get("unmatched_estimator_beams") or []
        rows_a.append(
            [
                key,
                str(s.get("model_beams") or p.get("discovered_model_beam_count") or 0),
                str(s.get("gt_beams") or p.get("discovered_estimator_beam_count") or 0),
                str(s.get("matched_beams") or p.get("matched_benchmark_population") or 0),
                str(len(um) if isinstance(um, list) else um),
                str(len(ug) if isinstance(ug, list) else ug),
            ]
        )
    lines += _md_table(["Set", "Model beams", "GT beams", "Matched", "Unmatched model", "Unmatched GT"], rows_a)
    lines += ["", "## TABLE B — VISION EXECUTION", ""]
    rows_b = []
    for key in INCLUDED_SET_KEYS:
        v = (vis.get("by_set") or {}).get(key) or {}
        rows_b.append(
            [
                key,
                str(v.get("eligible") or 0),
                str(v.get("attempted") or 0),
                str(v.get("new_live") or 0),
                str(v.get("reused") or 0),
                str(v.get("retried") or 0),
                str(v.get("api_success") or 0),
                str(v.get("schema_valid") or 0),
                str(v.get("usable") or 0),
                str(v.get("hybrid") or 0),
                str(v.get("fallback") or 0),
            ]
        )
    lines += _md_table(
        ["Set", "Eligible", "Attempted", "New live", "Reused", "Retried", "API success", "Schema valid", "Usable", "Hybrid", "Fallback"],
        rows_b,
    )
    lines += ["", "## TABLE C — ACCURACY BY SET", ""]
    rows_c = []
    for key in INCLUDED_SET_KEYS:
        s = per_set.get(key) or {}
        rows_c.append(
            [
                key,
                _fmt(s.get("beam_identification_percent")),
                _fmt(s.get("bar_identification_percent")),
                _fmt(s.get("correct_of_detected_percent")),
                _fmt(s.get("diameter_identification_percent")),
                _fmt(s.get("weight_accuracy_percent")),
                _fmt(s.get("overall_accuracy_percent")),
            ]
        )
    lines += _md_table(["Set", "Beam ID", "Bar ID", "Correct-of-detected", "Diameter", "Steel", "Overall"], rows_c)
    lines += ["", "## TABLE D — STEEL TOTALS", ""]
    rows_d = []
    for key in INCLUDED_SET_KEYS:
        s = per_set.get(key) or {}
        rows_d.append(
            [
                key,
                _fmt(s.get("hybrid_total_kg"), 3),
                _fmt(s.get("benchmark_total_kg"), 3),
                _fmt(s.get("signed_error_kg"), 3),
                _fmt(s.get("absolute_error_kg"), 3),
                _fmt(s.get("weight_accuracy_percent")),
            ]
        )
    lines += _md_table(["Set", "Model kg", "Benchmark kg", "Signed error", "Absolute error", "Steel accuracy"], rows_d)
    lines += ["", "## TABLE E — POOLED SECOND–SIXTH", ""]
    lines += _md_table(
        ["KPI", "Percent", "Numerator", "Denominator"],
        [
            ["Beam identification", _fmt(pooled.get("beam_identification_percent")), str(pooled.get("beam_n")), str(pooled.get("beam_d"))],
            ["Bar identification", _fmt(pooled.get("bar_identification_percent")), str(pooled.get("bar_n")), str(pooled.get("bar_d"))],
            ["Correct-of-detected", _fmt(pooled.get("correct_of_detected_percent")), str(pooled.get("correct_n")), str(pooled.get("correct_d"))],
            ["Diameter", _fmt(pooled.get("diameter_identification_percent")), str(pooled.get("diameter_n")), str(pooled.get("diameter_d"))],
            ["Steel/weight", _fmt(pooled.get("weight_accuracy_percent")), _fmt(pooled.get("hybrid_total_kg"), 3), _fmt(pooled.get("benchmark_total_kg"), 3)],
            ["Overall", _fmt(pooled.get("overall_accuracy_percent")), "mean of four pooled KPIs", "diameter excluded"],
        ],
    )
    lines += ["", "## TABLE F — SEMANTIC ERROR TAXONOMY", ""]
    lines += _md_table(["Code", "Count"], [[k, str(v)] for k, v in sorted(tax.items())])
    lines += ["", "## TABLE G — ENGINEERING ERROR TAXONOMY", ""]
    lines += _md_table(["Code", "Count"], [[k, str(v)] for k, v in sorted((eng or {}).items()) if k not in ("kind", "ranked")])
    lines += ["", "## TABLE H — COST / EXECUTION", ""]
    lines += _md_table(
        ["Item", "Value"],
        [
            ["New live", str(cost.get("new_live"))],
            ["Reused", str(cost.get("reused"))],
            ["Retried", str(cost.get("retried"))],
            ["API failed", str(cost.get("api_failed"))],
            ["Input tokens", str(cost.get("input_tokens"))],
            ["Output tokens", str(cost.get("output_tokens"))],
            ["Runtime s", str(cost.get("runtime_s"))],
        ],
    )
    dia = report_data.get("diameter_wise") or {}
    lines += ["", "## TABLE J — DIAMETER IDENTIFICATION (DETECTED BAR LINES)", ""]
    ident_rows = []
    for row in dia.get("identification_rows") or []:
        ident_rows.append(
            [
                str(row.get("diameter_label") or ""),
                str(row.get("gt_bar_lines") or 0),
                str(row.get("detected") or 0),
                str(row.get("match") or 0),
                str(row.get("wrong_diameter") or 0),
                _fmt(row.get("diameter_identification_percent")),
                str(row.get("note") or ""),
            ]
        )
    if ident_rows:
        lines += _md_table(["Diameter", "GT bar lines", "Detected", "MATCH", "WRONG_DIA", "Diameter ID", "Note"], ident_rows)
    else:
        lines.append("No diameter-wise identification rows.")
    lines += ["", str(dia.get("formula_identification") or ""), ""]
    lines += ["", "## TABLE K — DIAMETER-WISE STEEL QUANTITY", ""]
    steel_rows = []
    for row in dia.get("steel_rows") or []:
        steel_rows.append(
            [
                str(row.get("diameter_label") or ""),
                _fmt(row.get("benchmark_kg") if row.get("benchmark_kg") is not None else row.get("estimator_kg"), 3),
                _fmt(row.get("model_kg"), 3),
                _fmt(row.get("difference_kg"), 3),
                _fmt(row.get("difference_pct")),
                _fmt(row.get("quantity_ratio_percent")),
            ]
        )
    if steel_rows:
        lines += _md_table(
            ["Diameter", "Estimated kg", "Automated kg", "Difference kg", "Abs % diff", "Quantity ratio"],
            steel_rows,
        )
    else:
        lines.append("No diameter-wise steel rows.")
    lines += ["", str(dia.get("formula_steel") or ""), ""]
    lines += ["", "## TABLE I — SAFETY / IMMUTABILITY", ""]
    lines += _md_table(
        ["Item", "Value"],
        [
            ["PRODUCTION_WRITE", str(PRODUCTION_WRITE)],
            ["ENGINEERING_CHANGES", str(prod.get("engineering_changes"))],
            ["production_mutation_delta", str(prod.get("production_mutation_delta"))],
            ["changed_keys", json.dumps((result.get("fingerprints") or {}).get("changed_keys"))],
            ["LIVE_CLAUDE_CALL", str(result.get("live_claude_call"))],
        ],
    )
    (Path(out_root) / "validation_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_reports(*, out_root: Path, result: Dict[str, Any]) -> Dict[str, Any]:
    out_root = Path(out_root)
    by_set = result.get("by_set") or {}
    pop_all = result.get("population_all") or {}
    per_set_acc = {}
    vis_by = {}
    hybrid_by = {}
    steel_by = {}
    dia_by = {}
    dia_wise_by = {}
    ident_tables = []
    steel_tables = []
    perf_rows = {}
    tax_blocks = []
    full_blocks = []
    hy_blocks = []
    fb_blocks = []
    all_calcs = []
    truth_manifest = {}
    vision_fail_all = {"counts": {}, "by_set": {}}
    eng_all = {"counts": {}, "by_set": {}}
    sem_all = {"counts": {}, "by_set": {}}

    for key in INCLUDED_SET_KEYS:
        s = by_set.get(key) or {}
        pop = s.get("population") or {}
        scores = s.get("scores") or {}
        full = (scores.get("FULL_POPULATION") or {}).get("kpis") or {}
        hy = scores.get("HYBRID_ONLY") or {}
        fb = scores.get("FALLBACK_ONLY") or {}
        live_sum = s.get("live_summary") or {}
        calcs = s.get("calcs") or []
        all_calcs.extend(calcs)
        hy_ids = [c.get("beam_id") for c in calcs if c.get("provenance_kind") == "HYBRID"]
        fb_ids = [c.get("beam_id") for c in calcs if c.get("provenance_kind") == "FALLBACK"]
        n = max(len(calcs), 1)
        block = dict(full)
        per_set_acc[key] = display_block(block)
        per_set_acc[key].update(
            {
                "model_beams": pop.get("discovered_model_beam_count"),
                "gt_beams": pop.get("discovered_estimator_beam_count"),
                "matched_beams": pop.get("matched_benchmark_population"),
                "unmatched_model_count": len(pop.get("unmatched_model_beams") or []),
                "unmatched_gt_count": len(pop.get("unmatched_estimator_beams") or []),
                "hybrid_count": len(hy_ids),
                "fallback_count": len(fb_ids),
                "hybrid_percent": round(100.0 * len(hy_ids) / n, 2),
                "fallback_percent": round(100.0 * len(fb_ids) / n, 2),
                "truth_source": pop.get("truth_source"),
            }
        )
        vis_by[key] = {
            "eligible": (s.get("eligibility") or {}).get("counts", {}).get("VISION_ELIGIBLE"),
            "attempted": live_sum.get("attempted"),
            "new_live": live_sum.get("new_live"),
            "reused": live_sum.get("reused"),
            "retried": live_sum.get("retried"),
            "api_success": live_sum.get("api_success"),
            "schema_valid": live_sum.get("schema_valid"),
            "usable": live_sum.get("semantic_usable"),
            "hybrid": len(hy_ids),
            "fallback": len(fb_ids),
            "api_failed": live_sum.get("api_failed"),
            "not_available": live_sum.get("not_available"),
        }
        hybrid_by[key] = {
            "hybrid_count": len(hy_ids),
            "fallback_count": len(fb_ids),
            "FULL_POPULATION": scores.get("FULL_POPULATION"),
            "HYBRID_ONLY": hy,
            "FALLBACK_ONLY": fb,
        }
        steel_by[key] = {
            "model_kg": block.get("hybrid_total_kg"),
            "benchmark_kg": block.get("benchmark_total_kg"),
            "signed_error_kg": block.get("signed_error_kg"),
            "absolute_error_kg": block.get("absolute_error_kg"),
            "weight_accuracy_percent": block.get("weight_accuracy_percent"),
        }
        dia_by[key] = {
            "diameter_identification_percent": block.get("diameter_identification_percent"),
            "numerator": block.get("diameter_n"),
            "denominator": block.get("diameter_d"),
        }
        dw = scores.get("diameter_wise") or {}
        dia_wise_by[key] = {
            "identification_rows": dw.get("identification_rows") or [],
            "steel_rows": dw.get("steel_rows") or [],
        }
        ident_tables.append(dw.get("identification_rows") or [])
        steel_tables.append(dw.get("steel_rows") or [])
        perf_rows[key] = per_set_acc[key]
        if block:
            full_blocks.append(block)
            tax_blocks.append(block)
        if hy.get("applicable") and hy.get("kpis"):
            hy_blocks.append(hy["kpis"])
        if fb.get("applicable") and fb.get("kpis"):
            fb_blocks.append(fb["kpis"])
        truth_manifest[key] = {
            "truth_source": pop.get("truth_source"),
            "truth_context": pop.get("truth_context"),
            "path": pop.get("estimator_path"),
        }
        vf = s.get("vision_failures") or {"counts": {}}
        vision_fail_all["by_set"][key] = vf
        for ck, cv in (vf.get("counts") or {}).items():
            vision_fail_all["counts"][ck] = vision_fail_all["counts"].get(ck, 0) + int(cv or 0)
        ee = s.get("engineering_errors") or {"counts": {}}
        eng_all["by_set"][key] = ee
        for ck, cv in (ee.get("counts") or {}).items():
            eng_all["counts"][ck] = eng_all["counts"].get(ck, 0) + int(cv or 0)
        se = s.get("semantic_errors") or {"counts": {}}
        sem_all["by_set"][key] = se
        for ck, cv in (se.get("counts") or {}).items():
            sem_all["counts"][ck] = sem_all["counts"].get(ck, 0) + int(cv or 0)
        truth_map = {}
        wb = (pop.get("truth") or {}).get("workbook")
        if wb is not None:
            for b in getattr(wb, "beams", []) or []:
                truth_map[b.beam_id] = {"beam_id": b.beam_id, "steel_kg": b.steel_kg, "bar_count": len(b.bars or [])}
        for c in calcs:
            write_beam_review(out_root=out_root, set_key=key, calc=c, truth=truth_map.get(str(c.get("beam_id"))))

    pooled = display_block(pool_kpi_blocks(full_blocks))
    pooled["taxonomy"] = merge_taxonomy(tax_blocks)
    hy_pooled = pool_kpi_blocks(hy_blocks) if hy_blocks else None
    fb_pooled = pool_kpi_blocks(fb_blocks) if fb_blocks else None
    hy_n = sum(int((per_set_acc.get(k) or {}).get("hybrid_count") or 0) for k in INCLUDED_SET_KEYS)
    fb_n = sum(int((per_set_acc.get(k) or {}).get("fallback_count") or 0) for k in INCLUDED_SET_KEYS)
    tot = max(hy_n + fb_n, 1)
    live_all = result.get("live_summary") or {}
    report_data = {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "decision": result.get("decision"),
        "mode": result.get("mode"),
        "population": {
            "model_beam_total": pop_all.get("model_beam_total"),
            "estimator_beam_total": pop_all.get("estimator_beam_total"),
            "matched_total": pop_all.get("matched_total"),
            "excluded": pop_all.get("excluded"),
            "by_set": {k: slim_set_population(v) for k, v in (pop_all.get("by_set") or {}).items()},
        },
        "per_set": per_set_acc,
        "pooled": pooled,
        "vision_coverage": {
            "hybrid_count": hy_n,
            "fallback_count": fb_n,
            "hybrid_percent": round(100.0 * hy_n / tot, 2),
            "fallback_percent": round(100.0 * fb_n / tot, 2),
        },
        "vision_execution": {"by_set": vis_by, "pooled": live_all},
        "cohorts": {
            "HYBRID_ONLY": {"applicable": hy_pooled is not None, "kpis": display_block(hy_pooled) if hy_pooled else None},
            "FALLBACK_ONLY": {"applicable": fb_pooled is not None, "kpis": display_block(fb_pooled) if fb_pooled else None},
            "FULL_POPULATION": {"applicable": True, "kpis": pooled},
        },
        "semantic_taxonomy_pooled": pooled.get("taxonomy") or {},
        "engineering_errors": eng_all,
        "semantic_errors": sem_all,
        "cost": live_all,
        "limitations": result.get("limitations") or [],
        "conclusion": result.get("conclusion") or "",
        "fifth_reuse_decision": (result.get("fifth_reuse") or {}).get("decision"),
        "diameter_wise": {
            "by_set": dia_wise_by,
            "identification_rows": pool_identification_rows(ident_tables),
            "steel_rows": pool_steel_rows(steel_tables),
            "formula_identification": (
                "QA.2A diameter_accuracy_pct is an alias of bar matching (MATCH / detected) and is not used. "
                "A detected bar is diameter-correct unless status is WRONG_DIAMETER. "
                "GT diameter is the estimator line diameter. "
                "Pooled % uses summed raw counts, not the average of set percentages. "
                "Diameter remains excluded from overall."
            ),
            "formula_steel": (
                "Quantity ratio = automated kg / estimated kg x 100. It is not accuracy. "
                "A ratio above 100% is an overestimate. "
                "This is not the same as diameter identification."
            ),
        },
    }
    charts = write_charts(out_root=out_root, report_data=report_data)
    report_data["charts"] = charts
    _dump(out_root / "report_data.json", report_data)
    docx_path = write_docx(out_root=out_root, data=report_data, charts=charts)
    pdf_path = write_pdf(out_root=out_root, data=report_data)

    pop_manifest = {
        "included_set_keys": list(INCLUDED_SET_KEYS),
        "excluded": pop_all.get("excluded"),
        "model_beam_total": pop_all.get("model_beam_total"),
        "estimator_beam_total": pop_all.get("estimator_beam_total"),
        "matched_total": pop_all.get("matched_total"),
        "by_set": {k: slim_set_population(v) for k, v in (pop_all.get("by_set") or {}).items()},
    }
    _dump(out_root / "benchmark_population_manifest.json", pop_manifest)
    _dump(out_root / "second_to_sixth_population_summary.json", pop_manifest)
    _dump(out_root / "vision_execution_manifest.json", result.get("vision_execution_manifest") or vis_by)
    _dump(out_root / "vision_coverage_by_set.json", vis_by)
    _dump(out_root / "hybrid_execution_manifest.json", result.get("hybrid_execution_manifest") or {})
    _dump(out_root / "hybrid_results_by_set.json", hybrid_by)
    _dump(out_root / "benchmark_truth_manifest.json", truth_manifest)
    _dump(out_root / "per_set_accuracy_metrics.json", per_set_acc)
    _dump(out_root / "pooled_accuracy_metrics.json", pooled)
    _dump(out_root / "hybrid_fallback_cohort_metrics.json", report_data.get("cohorts"))
    _dump(out_root / "semantic_error_summary.json", sem_all)
    _dump(out_root / "engineering_error_summary.json", eng_all)
    _dump(out_root / "vision_failure_analysis.json", vision_fail_all)
    _dump(out_root / "steel_accuracy_by_set.json", steel_by)
    _dump(out_root / "diameter_accuracy_by_set.json", dia_by)
    _dump(out_root / "diameter_wise_identification.json", (report_data.get("diameter_wise") or {}).get("identification_rows"))
    _dump(out_root / "diameter_wise_steel.json", (report_data.get("diameter_wise") or {}).get("steel_rows"))
    _dump(out_root / "diameter_wise_by_set.json", dia_wise_by)
    _dump(out_root / "per_set_performance_summary.json", perf_rows)
    _dump(out_root / "source_fingerprint_check.json", result.get("fingerprints") or {})
    _dump(out_root / "production_mutation_check.json", result.get("production") or {})
    _dump(out_root / "anti_hardcoding_results.json", result.get("anti_hardcoding") or {})
    _dump(
        out_root / "validation_summary.json",
        {
            "decision": result.get("decision"),
            "unit_tests": {k: (result.get("unit_tests") or {}).get(k) for k in ("success", "passed", "total")},
            "fingerprints_unchanged": (result.get("fingerprints") or {}).get("unchanged"),
            "anti_hardcoding_ok": (result.get("anti_hardcoding") or {}).get("ok"),
        },
    )
    write_validation_report(out_root=out_root, result=result, report_data=report_data)
    slim = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "decision": result.get("decision"),
        "pass_fail": result.get("pass_fail"),
        "mode": result.get("mode"),
        "live_claude_call": result.get("live_claude_call"),
        "runtime_s": result.get("runtime_s"),
        "production": result.get("production"),
        "pooled": pooled,
        "per_set": {k: display_block(v) for k, v in per_set_acc.items()},
        "vision_coverage": report_data.get("vision_coverage"),
        "vision_execution": vis_by,
        "fifth_reuse": result.get("fifth_reuse"),
        "cost": live_all,
        "unit_tests": {kk: (result.get("unit_tests") or {}).get(kk) for kk in ("success", "passed", "total")},
        "fingerprints": {
            "unchanged": (result.get("fingerprints") or {}).get("unchanged"),
            "changed_keys": (result.get("fingerprints") or {}).get("changed_keys"),
        },
        "limitations": result.get("limitations"),
        "conclusion": result.get("conclusion"),
        "docx_path": str(docx_path),
        "pdf_path": str(pdf_path),
        "output_root": str(out_root),
    }
    _dump(out_root / "P2.6.10-E.3_RESULTS.json", slim)
    result["docx_path"] = str(docx_path)
    result["pdf_path"] = str(pdf_path)
    result["report_data"] = report_data
    return result


__all__ = ["write_reports"]
