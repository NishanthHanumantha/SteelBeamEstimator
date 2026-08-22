"""Presentation PDF from generated artefact data only. No typed KPI literals."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


PDF_NAME = "Steel_Beam_Estimation_Hybrid_Performance_Report_Fifth_Set.pdf"


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


def build_lines(out_root: Path) -> List[str]:
    data = _load(out_root / "accuracy_report_data.json")
    vis = _load(out_root / "vision_coverage_report.json")
    steel = data.get("steel") or {}
    beam = data.get("beam") or {}
    bar = data.get("bar") or {}
    cor = data.get("correct") or {}
    dia = data.get("diameter") or {}
    overall = data.get("overall") or {}
    results = _load(out_root / "P2.6.10-E.1_RESULTS.json")
    return [
        "STEEL BEAM ESTIMATION",
        "Current Hybrid Architecture Performance - Fifth Set",
        "Version 10  |  Hybrid Semantic Architecture  |  Fifth Set Benchmark",
        "",
        f"MODEL_VERSION: {results.get('model_version') or '10.11.22'}",
        f"GATE: {results.get('gate_version') or ''}",
        f"DECISION: {results.get('decision') or ''}",
        f"MODE: {results.get('mode') or 'OFFLINE_REPLAY'}",
        "",
        "Hybrid semantic authority: Claude Vision preferred after validation.",
        "Deterministic engineering authority: geometry, cut length, development",
        "length, spacers, stirrup engineering, steel calculation.",
        "This report is not a production-readiness claim.",
        "",
        "EXECUTIVE SUMMARY",
        f"Beam identification: {_fmt(beam.get('beam_identification_percent'))}%",
        f"Bar identification: {_fmt(bar.get('bar_identification_percent'))}%",
        f"Correct of detected bars: {_fmt(cor.get('correct_of_detected_percent'))}%",
        f"Diameter identification: {_fmt(dia.get('diameter_identification_percent'))}%",
        f"Steel accuracy: {_fmt(steel.get('weight_accuracy_percent'))}%",
        f"Overall accuracy: {_fmt(overall.get('overall_accuracy_percent'))}%",
        "",
        f"GT beams: {beam.get('total_ground_truth_beams')}  Detected: {beam.get('detected_ground_truth_beams')}",
        f"GT bars: {bar.get('total_ground_truth_bars')}  Identified: {bar.get('identified_ground_truth_bars')}",
        f"MATCH bars: {cor.get('fully_matched_detected_bars')}",
        f"Hybrid kg: {_fmt(steel.get('hybrid_total_kg'), 3)}",
        f"Benchmark kg: {_fmt(steel.get('benchmark_total_kg'), 3)}",
        f"Absolute kg error: {_fmt(steel.get('absolute_error_kg'), 3)}",
        "",
        "FORMULAS (QA.2A / QA.3.0)",
        "Beam ID = detected_gt_beams / total_gt_beams * 100",
        "Bar ID = identified_gt_bars / total_gt_bars * 100",
        "Correct of detected = MATCH / detected_bars * 100",
        "Steel = max(0, 100 - abs(hybrid-bench)/bench * 100)",
        "Overall = mean(beam ID, bar ID, correct of detected, steel)",
        "Diameter is reported separately and is not in the overall mean.",
        "",
        f"Vision usable beams (offline replay): {vis.get('usable_beam_count', 0)}",
        f"Vision scanned: {vis.get('scanned')}  api_failed: {vis.get('api_failed')}",
        "",
        "SCOPE",
        "Fifth Set only. No Second/Third/Fourth/Sixth comparison.",
        "No historical improvement claim. No production promotion.",
    ]


def write_pdf(*, out_root: Path) -> Path:
    out_root = Path(out_root)
    lines = build_lines(out_root)
    dest = out_root / PDF_NAME
    content_cmds = ["BT", "/F1 11 Tf"]
    y = 800
    for i, line in enumerate(lines):
        size = 16 if i == 0 else 12 if i in (1, 2) else 11
        if i == 0:
            content_cmds.append(f"/F1 {size} Tf")
        elif i == 3:
            content_cmds.append("/F1 11 Tf")
        content_cmds.append(f"1 0 0 1 48 {y} Tm ({_esc(line)}) Tj")
        y -= 16 if i > 2 else 20
        if y < 48:
            content_cmds.append("ET")
            content_cmds.append("BT")
            content_cmds.append("/F1 11 Tf")
            y = 800
    content_cmds.append("ET")
    stream = "\n".join(content_cmds).encode("latin-1", errors="replace")
    objects = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    add(b"<< /Type /Catalog /Pages 2 0 R >>")
    add(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    add(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
    )
    header = f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
    add(header + stream + b"\nendstream")
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
