"""Stakeholder PDF from the same report_data.json as the DOCX."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import GATE_VERSION, INCLUDED_SET_KEYS, MODEL_VERSION, PDF_NAME, PHASE_ID


def _esc(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _fmt(v: Any, n: int = 2, suffix: str = "") -> str:
    if v is None:
        return "-"
    try:
        return f"{float(v):.{n}f}{suffix}"
    except (TypeError, ValueError):
        return str(v)


def build_lines(data: Dict[str, Any]) -> List[str]:
    pooled = data.get("pooled") or {}
    per_set = data.get("per_set") or {}
    cov = data.get("vision_coverage") or {}
    pop = data.get("population") or {}
    vis_exec = data.get("vision_execution") or {}
    tax = data.get("semantic_taxonomy_pooled") or {}
    eng = (data.get("engineering_errors") or {}).get("counts") or data.get("engineering_errors") or {}
    cost = data.get("cost") or {}
    coh = data.get("cohorts") or {}
    lines = [
        "STEEL BEAM ESTIMATION",
        "Current Hybrid Architecture Performance",
        "Second to Sixth Drawing Sets  |  Version 10",
        "",
        f"MODEL_VERSION: {data.get('model_version') or MODEL_VERSION}",
        f"GATE: {data.get('gate_version') or GATE_VERSION}",
        f"PHASE: {PHASE_ID}",
        f"DECISION: {data.get('decision') or '-'}",
        f"BENCHMARK MODE: {data.get('mode') or '-'}",
        "Confidential / internal use. Shadow benchmark. Not a production promotion.",
        "",
        "1. EXECUTIVE SUMMARY",
        "Five-set current hybrid architecture: Claude Vision semantics + deterministic engineering.",
        f"Model beams: {pop.get('model_beam_total')}  GT beams: {pop.get('estimator_beam_total')}  Matched: {pop.get('matched_total')}",
        f"HYBRID: {cov.get('hybrid_count')} ({_fmt(cov.get('hybrid_percent'), suffix='%')})  FALLBACK: {cov.get('fallback_count')} ({_fmt(cov.get('fallback_percent'), suffix='%')})",
        f"Pooled beam identification: {_fmt(pooled.get('beam_identification_percent'), suffix='%')}  ({pooled.get('beam_n')} / {pooled.get('beam_d')})",
        f"Pooled bar identification: {_fmt(pooled.get('bar_identification_percent'), suffix='%')}  ({pooled.get('bar_n')} / {pooled.get('bar_d')})",
        f"Pooled correct-of-detected: {_fmt(pooled.get('correct_of_detected_percent'), suffix='%')}  ({pooled.get('correct_n')} / {pooled.get('correct_d')})",
        f"Pooled diameter identification: {_fmt(pooled.get('diameter_identification_percent'), suffix='%')}",
        f"Pooled steel/weight accuracy: {_fmt(pooled.get('weight_accuracy_percent'), suffix='%')}",
        f"Pooled overall accuracy: {_fmt(pooled.get('overall_accuracy_percent'), suffix='%')}",
        f"Model kg: {_fmt(pooled.get('hybrid_total_kg'), 3)}  Benchmark kg: {_fmt(pooled.get('benchmark_total_kg'), 3)}",
        "",
        "2. CURRENT HYBRID ARCHITECTURE",
        "DXF -> Beam discovery -> Deterministic geometry context -> Claude Vision",
        "-> D.1 semantic authority contract -> D.2 hybrid resolution",
        "-> D.3 engineering binding -> D.4 shadow engineering calculation",
        "-> accuracy benchmark.",
        "VISION SEMANTICS: target identity, layer, groups, bar count, diameter,",
        "specification, MAIN/EXTRA, support scope, stirrup identification.",
        "DETERMINISTIC ENGINEERING: spacers, geometry, cut length, development,",
        "anchorage, hooks, stirrup engineering, pieces, weight, BBS, workbook.",
        "Vision-preferred is validated, not blindly accepted.",
        "",
        "3. BENCHMARK SCOPE AND POPULATION",
        "Second, Third, Fourth, Fifth, Sixth. First Set excluded.",
    ]
    for key in INCLUDED_SET_KEYS:
        row = (pop.get("by_set") or {}).get(key) or per_set.get(key) or {}
        lines.append(
            f"{key}: model={row.get('model_beams') or row.get('discovered_model_beam_count')} "
            f"GT={row.get('gt_beams') or row.get('discovered_estimator_beam_count')} "
            f"matched={row.get('matched_beams') or row.get('matched_benchmark_population')} "
            f"truth={row.get('truth_source')}"
        )
    lines += ["", "4. VISION EXECUTION AND HYBRID COVERAGE"]
    for key in INCLUDED_SET_KEYS:
        row = (vis_exec.get("by_set") or {}).get(key) or {}
        lines.append(
            f"{key}: eligible={row.get('eligible')} attempted={row.get('attempted')} "
            f"new={row.get('new_live')} reused={row.get('reused')} retried={row.get('retried')} "
            f"api={row.get('api_success')} schema={row.get('schema_valid')} usable={row.get('usable')} "
            f"HYBRID={row.get('hybrid')} FALLBACK={row.get('fallback')}"
        )
    lines += [
        f"Fifth Set reuse decision: {data.get('fifth_reuse_decision')}",
        "",
        "5. ACCURACY BY DRAWING SET",
    ]
    for key in INCLUDED_SET_KEYS:
        row = per_set.get(key) or {}
        lines.append(
            f"{key}: beam={_fmt(row.get('beam_identification_percent'), suffix='%')} "
            f"bar={_fmt(row.get('bar_identification_percent'), suffix='%')} "
            f"correct={_fmt(row.get('correct_of_detected_percent'), suffix='%')} "
            f"diameter={_fmt(row.get('diameter_identification_percent'), suffix='%')} "
            f"steel={_fmt(row.get('weight_accuracy_percent'), suffix='%')} "
            f"overall={_fmt(row.get('overall_accuracy_percent'), suffix='%')}"
        )
    lines += [
        "",
        "6. POOLED SECOND-TO-SIXTH PERFORMANCE",
        "Headline KPIs pool raw numerators and denominators. Steel kg is pooled before accuracy.",
        "Set percentages are not averaged for the headline overall score.",
        f"Overall = mean(beam ID, bar ID, correct-of-detected, steel/weight). Diameter excluded.",
        "",
        "7. DIAMETER IDENTIFICATION (DETECTED BAR LINES)",
        "QA.2A diameter_accuracy_pct is MATCH/detected and is not used here.",
        "A detected bar is diameter-correct unless status is WRONG_DIAMETER.",
        "GT diameter is the estimator line diameter. Pooled from raw counts. Diameter excluded from overall.",
    ]
    dia = data.get("diameter_wise") or {}
    ident = dia.get("identification_rows") or []
    if ident:
        lines.append("Diameter | GT bar lines | Detected | MATCH | WRONG_DIA | Diameter ID | Note")
        for row in ident:
            lines.append(
                f"{row.get('diameter_label')}: GT={row.get('gt_bar_lines')} detected={row.get('detected')} "
                f"MATCH={row.get('match')} WRONG_DIA={row.get('wrong_diameter')} "
                f"ID={_fmt(row.get('diameter_identification_percent'), suffix='%')} "
                f"{row.get('note') or ''}".strip()
            )
    else:
        lines.append("No diameter-wise identification rows.")
    lines += [
        "",
        "8. DIAMETER-WISE STEEL QUANTITY (NOT THE SAME AS DIAMETER IDENTIFICATION)",
        "Quantity ratio = automated kg / estimated kg x 100. It is not accuracy.",
        "A ratio above 100% is an overestimate. kg pooled before difference and ratio.",
    ]
    steel_rows = dia.get("steel_rows") or []
    if steel_rows:
        lines.append("Diameter | Estimated kg | Automated kg | Difference kg | Abs % diff | Quantity ratio")
        for row in steel_rows:
            ratio = row.get("quantity_ratio_percent")
            ratio_s = "-" if ratio is None else f"{float(ratio):.0f}%"
            lines.append(
                f"{row.get('diameter_label')}: est={_fmt(row.get('benchmark_kg') if row.get('benchmark_kg') is not None else row.get('estimator_kg'), 0)} "
                f"auto={_fmt(row.get('model_kg'), 0)} diff={_fmt(row.get('difference_kg'), 0)} "
                f"abs={_fmt(row.get('difference_pct'), 1, suffix='%')} ratio={ratio_s}"
            )
    else:
        lines.append("No diameter-wise steel rows.")
    lines += [
        "",
        "9. SEMANTIC ERROR PROFILE",
    ]
    for k, v in sorted((tax or {}).items(), key=lambda kv: -int(kv[1] or 0)):
        lines.append(f"{k}: {v}")
    lines += ["", "10. ENGINEERING CALCULATION PROFILE"]
    if isinstance(eng, dict):
        for k, v in eng.items():
            if k in ("kind", "ranked"):
                continue
            lines.append(f"{k}: {v}")
    lines += ["", "11. HYBRID / FALLBACK COHORTS (pooled applicable subsets)"]
    for label in ("HYBRID_ONLY", "FALLBACK_ONLY", "FULL_POPULATION"):
        block = coh.get(label) or {}
        if not block.get("applicable"):
            lines.append(f"{label}: NOT_APPLICABLE")
        else:
            k = block.get("kpis") or block
            lines.append(
                f"{label}: beam={_fmt(k.get('beam_identification_percent'), suffix='%')} "
                f"bar={_fmt(k.get('bar_identification_percent'), suffix='%')} "
                f"correct={_fmt(k.get('correct_of_detected_percent'), suffix='%')} "
                f"steel={_fmt(k.get('weight_accuracy_percent'), suffix='%')} "
                f"overall={_fmt(k.get('overall_accuracy_percent'), suffix='%')}"
            )
    lines += [
        "",
        "12. CURRENT WORKFLOW VALUE",
        "Model-assisted estimation. Estimator verification required.",
        "Accuracy is not equivalent to time saved. No time study in this phase.",
        "Do not treat Vision API success as engineering accuracy.",
        "",
        "13. METHODOLOGY, SOURCES AND LIMITATIONS",
        "Truth: estimator Excel (evaluation-only). QA.2A BeamMatcher / BarMatcher / metric8.",
        "QA.3.0 four-KPI overall. Ground truth is never used in runtime semantic resolution.",
        f"Limitations: {', '.join(data.get('limitations') or [])}",
        f"PRODUCTION_WRITE=false  ENGINEERING_CHANGES=NONE  shadow_only=true",
        "",
        "COST / EXECUTION",
        f"New live: {cost.get('new_live')}  Reused: {cost.get('reused')}  Retried: {cost.get('retried')}  Failed: {cost.get('api_failed')}",
        f"Input tokens: {cost.get('input_tokens')}  Output tokens: {cost.get('output_tokens')}  Runtime s: {cost.get('runtime_s')}",
        "",
        "CONCLUSION",
        str(data.get("conclusion") or ""),
        "No historical improvement claim. No production readiness claim.",
    ]
    return lines


def _page_content(lines: List[str], first_page: bool) -> bytes:
    content_cmds = ["BT", "/F1 11 Tf"]
    y = 800
    for i, line in enumerate(lines):
        if first_page:
            size = 16 if i == 0 else 12 if i in (1, 2) else 10
            if i == 0:
                content_cmds.append(f"/F1 {size} Tf")
            elif i == 3:
                content_cmds.append("/F1 10 Tf")
        else:
            if i == 0:
                content_cmds.append("/F1 10 Tf")
        content_cmds.append(f"1 0 0 1 48 {y} Tm ({_esc(line)}) Tj")
        y -= 14 if (not first_page or i > 2) else 18
    content_cmds.append("ET")
    return "\n".join(content_cmds).encode("latin-1", errors="replace")


def _chunk(lines: List[str], first_n: int = 46, rest_n: int = 50) -> List[List[str]]:
    if not lines:
        return [[]]
    pages = [lines[:first_n]]
    rest = lines[first_n:]
    while rest:
        pages.append(rest[:rest_n])
        rest = rest[rest_n:]
    return pages


def write_pdf(*, out_root: Path, data: Optional[Dict[str, Any]] = None) -> Path:
    out_root = Path(out_root)
    if data is None:
        path = out_root / "report_data.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    pages_lines = _chunk(build_lines(data))
    dest = out_root / PDF_NAME
    streams = [_page_content(chunk, first_page=(i == 0)) for i, chunk in enumerate(pages_lines)]
    n_pages = len(streams)
    objects: List[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    font_id = 3 + n_pages * 2
    page_ids = [3 + i * 2 for i in range(n_pages)]
    content_ids = [4 + i * 2 for i in range(n_pages)]
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    add(b"<< /Type /Catalog /Pages 2 0 R >>")
    add(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode("ascii"))
    for i in range(n_pages):
        add(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Contents {content_ids[i]} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>"
            ).encode("ascii")
        )
        header = f"<< /Length {len(streams[i])} >>\nstream\n".encode("ascii")
        add(header + streams[i] + b"\nendstream")
    add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    xref_offsets = [0]
    body = b"%PDF-1.4\n"
    for i, obj in enumerate(objects, start=1):
        xref_offsets.append(len(body))
        body += f"{i} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"
    xref_pos = len(body)
    xref = f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode("ascii")
    for off in xref_offsets[1:]:
        xref += f"{off:010d} 00000 n \n".encode("ascii")
    trailer = (
        f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    dest.write_bytes(body + xref + trailer)
    return dest


__all__ = ["build_lines", "write_pdf"]
