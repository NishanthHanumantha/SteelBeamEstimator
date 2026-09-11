"""Presentation PDF from generated artefact data. HYBRID / FALLBACK / FULL sections."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import PDF_NAME


def _esc(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _load(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _fmt(v: Any, n: int = 2) -> str:
    if v is None:
        return "-"
    try:
        return f"{float(v):.{n}f}"
    except (TypeError, ValueError):
        return str(v)


def _cohort_lines(title: str, block: Dict[str, Any], applicable: bool) -> List[str]:
    if not applicable:
        return [title, "Not applicable / insufficient comparison evidence.", ""]
    return [
        title,
        f"Beam identification: {_fmt(block.get('beam_identification_percent'))}%  ({block.get('beam_n')} / {block.get('beam_d')})",
        f"Bar identification: {_fmt(block.get('bar_identification_percent'))}%  ({block.get('bar_n')} / {block.get('bar_d')})",
        f"Correct of detected: {_fmt(block.get('correct_of_detected_percent'))}%  ({block.get('correct_n')} / {block.get('correct_d')})",
        f"Diameter identification: {_fmt(block.get('diameter_identification_percent'))}%",
        f"Steel accuracy: {_fmt(block.get('weight_accuracy_percent'))}%",
        f"Overall accuracy: {_fmt(block.get('overall_accuracy_percent'))}%",
        f"Model kg: {_fmt(block.get('hybrid_total_kg'), 3)}  Bench kg: {_fmt(block.get('benchmark_total_kg'), 3)}",
        f"Signed kg error: {_fmt(block.get('signed_error_kg'), 3)}  Abs kg error: {_fmt(block.get('absolute_error_kg'), 3)}",
        "",
    ]


def build_lines(out_root: Path) -> List[str]:
    data = _load(out_root / "accuracy_report_data.json")
    results = _load(out_root / "P2.6.10-E.2_RESULTS.json")
    vis = results.get("vision_coverage") or _load(out_root / "vision_eligibility_manifest.json")
    if isinstance(vis, dict) and "counts" in vis:
        vis = vis.get("counts") or vis
    prov = results.get("execution_provenance") or {}
    live = results.get("live_summary") or {}
    fail = results.get("vision_failures") or _load(out_root / "vision_failure_analysis.json")
    appl = data.get("applicable") or {}
    lim = results.get("limitations") or []
    lines = [
        "STEEL BEAM ESTIMATION",
        "Current Hybrid Architecture Performance - Fifth Set",
        "Version 10  |  Live Vision Hybrid Benchmark  |  Fifth Set",
        "",
        f"MODEL_VERSION: {results.get('model_version') or ''}",
        f"GATE: {results.get('gate_version') or ''}",
        f"DECISION: {results.get('decision') or ''}",
        f"LIVE_COMPLETION: {results.get('live_completion') or ''}",
        f"MODE: {results.get('mode') or ''}",
        "",
        "Hybrid semantic authority: Claude Vision preferred after validation.",
        "Deterministic engineering authority: geometry, cut length, development",
        "length, spacers, stirrup engineering, steel calculation.",
        "This report is not a production-readiness claim.",
        "No previous-vs-current comparison is included.",
        "",
        "EXECUTION PROVENANCE",
        f"HYBRID beams: {prov.get('hybrid_count')}  ({_fmt(prov.get('hybrid_percent'))}%)",
        f"FALLBACK beams: {prov.get('fallback_count')}  ({_fmt(prov.get('fallback_percent'))}%)",
        f"VISION_REUSED: {prov.get('VISION_REUSED')}",
        f"VISION_RETRIED_AFTER_HISTORICAL_FAILURE: {prov.get('VISION_RETRIED_AFTER_HISTORICAL_FAILURE')}",
        f"VISION_NEW_LIVE_CALL: {prov.get('VISION_NEW_LIVE_CALL')}",
        "",
        "VISION COVERAGE",
        f"READY: {vis.get('VISION_READY')}  LIMITED: {vis.get('VISION_READY_WITH_LIMITATIONS')}",
        f"NOT_READY: {vis.get('VISION_NOT_READY')}  Eligible: {vis.get('VISION_ELIGIBLE')}",
        f"Blocked: {vis.get('VISION_BLOCKED_NOT_READY')}  Source available: {vis.get('visual_source_available')}",
        f"Attempted: {live.get('attempted')}  API success: {live.get('api_success')}  API failed: {live.get('api_failed')}",
        f"Schema valid: {live.get('schema_valid')}  Semantic usable: {live.get('semantic_usable')}",
        "",
    ]
    lines += _cohort_lines("HYBRID POPULATION", data.get("hybrid") or {}, bool(appl.get("HYBRID_ONLY", True)))
    lines += _cohort_lines("FALLBACK POPULATION", data.get("fallback") or {}, bool(appl.get("FALLBACK_ONLY", True)))
    lines += _cohort_lines("FULL POPULATION", data.get("full") or {}, bool(appl.get("FULL_POPULATION", True)))
    lines += [
        "VISION FAILURE ANALYSIS",
        f"Counts: {json.dumps((fail.get('counts') if isinstance(fail, dict) else {}) or {}, default=str)}",
        f"Historical API recovered: {(fail.get('historical_api_recovered') if isinstance(fail, dict) else None)}",
        "",
        "COST / EXECUTION",
        f"Retries: {live.get('retries')}  Reused: {live.get('reused')}",
        f"Input tokens: {live.get('input_tokens')}  Output tokens: {live.get('output_tokens')}",
        f"Runtime s: {results.get('runtime_s')}",
        "",
        "FORMULAS (QA.2A / QA.3.0)",
        "Beam ID = detected_gt_beams / total_gt_beams * 100",
        "Bar ID = identified_gt_bars / total_gt_bars * 100",
        "Correct of detected = MATCH / detected_bars * 100",
        "Steel = max(0, 100 - abs(hybrid-bench)/bench * 100)",
        "Overall = mean(beam ID, bar ID, correct of detected, steel)",
        "Diameter is reported separately and is not in the overall mean.",
        "Subset scores use matching estimator+model IDs only.",
        "",
        "Ground truth: ESTIMATOR_EXCEL. Workbook mapping may not perfectly",
        "represent physical drawing interpretation.",
        "",
        "LIMITATIONS",
    ]
    for item in lim:
        lines.append(f"- {item}")
    lines += [
        "",
        "CONCLUSION",
        str(results.get("conclusion") or ""),
        "",
        "SCOPE",
        "Fifth Set only. No Second/Third/Fourth/Sixth comparison.",
        "No historical improvement claim. No production promotion.",
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


def write_pdf(*, out_root: Path) -> Path:
    out_root = Path(out_root)
    pages_lines = _chunk(build_lines(out_root))
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


__all__ = ["PDF_NAME", "write_pdf"]
