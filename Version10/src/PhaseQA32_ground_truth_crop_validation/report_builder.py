"""
Write QA.3.2 diagnostic artefacts.
MODEL_VERSION: 10.0.2
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

MODEL_VERSION = "10.0.2"
PHASE_ID = "QA.3.2"


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _try_xlsx(path: Path, rows: List[Dict[str, Any]]) -> None:
    try:
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "GroundTruthCrop"
        if not rows:
            wb.save(path)
            return
        headers = list(rows[0].keys())
        ws.append(headers)
        for r in rows:
            ws.append([r.get(h) for h in headers])
        wb.save(path)
        return
    except Exception:
        pass
    # Minimal OOXML workbook fallback (no openpyxl)
    import csv
    import io
    import zipfile

    headers = list(rows[0].keys()) if rows else ["beam_id"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow([r.get(h) for h in headers])
    # Also write CSV sibling for convenience
    path.with_suffix(".csv").write_text(buf.getvalue(), encoding="utf-8")
    # Empty valid-ish xlsx placeholder: store sheet as shared strings text via zip
    sheet_rows = [headers] + [[r.get(h) for h in headers] for r in rows]

    def _cell(ref: str, val: Any) -> str:
        if val is None:
            return f'<c r="{ref}"/>'
        s = str(val).replace("&", "&amp;").replace("<", "&lt;")
        return f'<c r="{ref}" t="inlineStr"><is><t>{s}</t></is></c>'

    def _col(i: int) -> str:
        n = i
        out = ""
        while True:
            out = chr(ord("A") + (n % 26)) + out
            n = n // 26 - 1
            if n < 0:
                break
        return out

    row_xml = []
    for ri, row in enumerate(sheet_rows, start=1):
        cells = "".join(_cell(f"{_col(ci)}{ri}", v) for ci, v in enumerate(row))
        row_xml.append(f'<row r="{ri}">{cells}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData></worksheet>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    wb_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="GroundTruthCrop" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", wb_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)


def write_all(
    out_root: Path,
    records: List[Dict[str, Any]],
    aggregate: Dict[str, Any],
    recommendations: Dict[str, Any],
    meta: Dict[str, Any],
) -> Dict[str, str]:
    out_root.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}
    now = datetime.now(timezone.utc).isoformat()

    main = {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "generated_at": now,
        **meta,
        "beams": records,
        "aggregate": aggregate,
        "recommendations": recommendations,
    }
    p = out_root / "GroundTruthCropValidation.json"
    _dump(p, main)
    paths[p.name] = str(p)

    # Excel rows
    xrows = []
    for r in records:
        d = r.get("decision") or {}
        m = r.get("alignment_metrics") or {}
        e = r.get("entity_completeness") or {}
        a = r.get("beam_alignment") or {}
        xrows.append(
            {
                "beam_id": r.get("beam_id"),
                "category": d.get("category"),
                "status": d.get("status"),
                "confidence": d.get("confidence"),
                "qa31_trust": d.get("qa31_ownership_conclusion_still_valid"),
                "iou": m.get("iou"),
                "overlap_pct": m.get("overlap_pct_actual_in_expected"),
                "centroid_error": m.get("centroid_error"),
                "completeness_pct": e.get("completeness_pct"),
                "beam_centred": a.get("beam_centred"),
                "beam_clipped": a.get("beam_clipped"),
                "excess_whitespace": a.get("excess_whitespace"),
                "neighbour_intrusion": a.get("neighbour_beam_intrusion"),
                "manual_regenerated": (r.get("manual_source") or {}).get("regenerated"),
                "reason": d.get("reason"),
            }
        )
    xp = out_root / "GroundTruthCropValidation.xlsx"
    _try_xlsx(xp, xrows)
    paths[xp.name] = str(xp)

    registry = {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "beams": [
            {
                "beam_id": r["beam_id"],
                "drawing_set": r.get("drawing_set"),
                "manual_png": (r.get("artefacts") or {}).get("manual_png"),
                "owned_render_png": (r.get("artefacts") or {}).get("owned_render_png"),
                "manual_source": r.get("manual_source"),
                "category": (r.get("decision") or {}).get("category"),
                "status": (r.get("decision") or {}).get("status"),
            }
            for r in records
        ],
    }
    p = out_root / "GroundTruthBeamRegistry.json"
    _dump(p, registry)
    paths[p.name] = str(p)

    p = out_root / "CropAlignmentMetrics.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "beams": [
                {"beam_id": r["beam_id"], **(r.get("alignment_metrics") or {})}
                for r in records
            ],
            "averages": {
                k: aggregate.get(k)
                for k in (
                    "average_crop_overlap",
                    "average_iou",
                    "average_alignment_error",
                    "average_centroid_error",
                    "average_padding_error",
                )
            },
        },
    )
    paths[p.name] = str(p)

    p = out_root / "CoordinateValidation.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "beams": [
                {"beam_id": r["beam_id"], **(r.get("coordinate_validation") or {})}
                for r in records
            ],
        },
    )
    paths[p.name] = str(p)

    p = out_root / "EntityCompleteness.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "beams": [
                {
                    "beam_id": r["beam_id"],
                    **(r.get("entity_completeness") or {}),
                    "expected_counts": ((r.get("steps") or {}).get("5_entity_completeness") or {}).get(
                        "expected_counts"
                    ),
                    "manual_counts": ((r.get("steps") or {}).get("5_entity_completeness") or {}).get(
                        "manual_counts"
                    ),
                }
                for r in records
            ],
        },
    )
    paths[p.name] = str(p)

    p = out_root / "BeamAlignmentDiagnostics.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "beams": [
                {"beam_id": r["beam_id"], **(r.get("beam_alignment") or {})}
                for r in records
            ],
        },
    )
    paths[p.name] = str(p)

    p = out_root / "GroundTruthDecisionMatrix.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "definitions": {
                "A": "Ground truth crop is correct — ownership diagnosis remains valid",
                "B": "Ground truth crop partially incorrect — ownership diagnosis requires review",
                "C": "Ground truth crop incorrect — QA.3.1 conclusion cannot be trusted for this beam",
            },
            "beams": [
                {
                    "beam_id": r["beam_id"],
                    **(r.get("decision") or {}),
                    "validation_checks": r.get("validation_checks"),
                }
                for r in records
            ],
            "counts": aggregate.get("category_counts"),
        },
    )
    paths[p.name] = str(p)

    p = out_root / "GroundTruthSummary.json"
    _dump(
        p,
        {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": now,
            "aggregate": aggregate,
            "recommendations": recommendations,
            "answers": _global_answers(records, aggregate),
        },
    )
    paths[p.name] = str(p)

    # Markdown reports
    cards = _cards_md(records)
    p = out_root / "GroundTruthDiagnosticCards.md"
    p.write_text(cards, encoding="utf-8")
    paths[p.name] = str(p)

    p = out_root / "GroundTruthOverlayReport.md"
    p.write_text(_overlay_md(records, out_root), encoding="utf-8")
    paths[p.name] = str(p)

    p = out_root / "GroundTruthHeatmap.md"
    p.write_text(_heatmap_md(records, aggregate), encoding="utf-8")
    paths[p.name] = str(p)

    p = out_root / "GroundTruthRecommendations.md"
    p.write_text(_recs_md(recommendations, aggregate), encoding="utf-8")
    paths[p.name] = str(p)

    p = out_root / "README.md"
    p.write_text(_readme_md(meta, aggregate), encoding="utf-8")
    paths[p.name] = str(p)

    return paths


def write_execution_summary(
    out_root: Path,
    aggregate: Dict[str, Any],
    recommendations: Dict[str, Any],
    validation: Dict[str, Any],
    elapsed: float,
) -> Path:
    lines = [
        f"# Phase {PHASE_ID} Execution Summary",
        "",
        f"- MODEL_VERSION: `{MODEL_VERSION}`",
        f"- Elapsed: `{elapsed}s`",
        f"- Beams analysed: `{aggregate.get('beams_analysed')}`",
        f"- VALID / PARTIAL / INVALID: "
        f"`{aggregate.get('manual_crops_fully_correct')}` / "
        f"`{aggregate.get('manual_crops_partially_correct')}` / "
        f"`{aggregate.get('manual_crops_incorrect')}`",
        f"- Category A/B/C: `{aggregate.get('category_counts')}`",
        f"- Average IoU: `{aggregate.get('average_iou')}`",
        f"- Average completeness %: `{aggregate.get('average_completeness_pct')}`",
        f"- Regenerated manual crops: `{aggregate.get('regenerated_manual_crops')}`",
        f"- QA.3.1 trustworthy beams: `{aggregate.get('qa31_trustworthy_beam_count')}`",
        f"- Dominant finding: `{aggregate.get('dominant_finding')}`",
        f"- Validation overall_pass: `{validation.get('overall_pass')}`",
        "",
        "## Priorities",
    ]
    for pr in recommendations.get("priorities") or []:
        lines.append(f"### Priority {pr.get('priority')}: {pr.get('title')}")
        lines.append("")
        lines.append(pr.get("recommendation") or "")
        lines.append("")
    path = out_root / "ExecutionSummary.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _global_answers(records: List[Dict[str, Any]], agg: Dict[str, Any]) -> Dict[str, Any]:
    n = len(records)
    dxf_ok = sum(1 for r in records if (r.get("validation_checks") or {}).get("correct_reinforcement_dxf_selected"))
    beam_ok = sum(1 for r in records if (r.get("validation_checks") or {}).get("correct_beam_located"))
    geo_ok = sum(1 for r in records if (r.get("validation_checks") or {}).get("manual_crop_spatially_matches_reconstructed"))
    ent_ok = sum(1 for r in records if (r.get("validation_checks") or {}).get("manual_crop_contains_all_expected_entities"))
    coord_ok = sum(1 for r in records if (r.get("validation_checks") or {}).get("coordinate_transforms_valid"))
    trust = int(agg.get("qa31_trustworthy_beam_count") or 0)
    return {
        "1_correct_reinforcement_dxf_used": f"{dxf_ok}/{n}",
        "2_correct_beam_located": f"{beam_ok}/{n}",
        "3_manual_crop_geometrically_correct": f"{geo_ok}/{n} fully match reconstructed",
        "4_manual_contains_all_expected_entities": f"{ent_ok}/{n}",
        "5_coordinate_or_transform_error": f"{n - coord_ok}/{n} with notes/issues",
        "6_manual_crop_trustworthy_ground_truth": trust == n and n > 0,
        "7_qa31_ownership_diagnosis_can_be_trusted": trust == n and n > 0,
        "8_pipeline_divergence": agg.get("dominant_finding"),
    }


def _cards_md(records: List[Dict[str, Any]]) -> str:
    lines = [f"# {PHASE_ID} Ground Truth Diagnostic Cards", "", f"MODEL_VERSION: {MODEL_VERSION}", ""]
    for r in records:
        d = r.get("decision") or {}
        m = r.get("alignment_metrics") or {}
        e = r.get("entity_completeness") or {}
        a = r.get("beam_alignment") or {}
        s = r.get("manual_source") or {}
        lines += [
            f"## {r.get('beam_id')}",
            "",
            f"- **Category**: {d.get('category')} — {d.get('status')} (confidence {d.get('confidence')})",
            f"- **QA.3.1 trust**: {d.get('qa31_ownership_conclusion_still_valid')}",
            f"- **Manual source**: {s.get('source_kind')} (regenerated={s.get('regenerated')})",
            f"- **IoU**: {m.get('iou')} | overlap%={m.get('overlap_pct_actual_in_expected')} | centroid_err={m.get('centroid_error')}",
            f"- **Completeness %**: {e.get('completeness_pct')} (missing_bars={e.get('missing_bars')}, missing_ann={e.get('missing_annotations')})",
            f"- **Alignment**: centred={a.get('beam_centred')} clipped={a.get('beam_clipped')} whitespace={a.get('excess_whitespace')} neighbour={a.get('neighbour_beam_intrusion')}",
            f"- **Reason**: {d.get('reason')}",
            f"- **Overlay**: {(r.get('overlay') or {}).get('overlay_path')}",
            "",
        ]
    return "\n".join(lines)


def _overlay_md(records: List[Dict[str, Any]], out_root: Path) -> str:
    lines = [
        f"# {PHASE_ID} Overlay Report",
        "",
        "Colour key: Expected=Green, Manual=Red, Shared=Yellow, Missing=Blue",
        "",
        f"Directory: `{out_root / 'ExpectedCrop_vs_ManualCrop'}`",
        "",
    ]
    for r in records:
        ov = r.get("overlay") or {}
        lines.append(f"## {r.get('beam_id')}")
        lines.append(f"- Overlay: `{ov.get('overlay_path')}`")
        lines.append(f"- Heatmap: `{ov.get('heatmap_path')}`")
        lines.append(f"- Error: `{ov.get('error')}`")
        lines.append("")
    return "\n".join(lines)


def _heatmap_md(records: List[Dict[str, Any]], agg: Dict[str, Any]) -> str:
    lines = [
        f"# {PHASE_ID} Ground Truth Heatmap",
        "",
        f"| Beam | Category | Status | IoU | Completeness% | CentroidErr | Regenerated | QA31 Trust |",
        f"|---|---|---|---:|---:|---:|---|---|",
    ]
    for r in records:
        d = r.get("decision") or {}
        m = r.get("alignment_metrics") or {}
        e = r.get("entity_completeness") or {}
        lines.append(
            f"| {r.get('beam_id')} | {d.get('category')} | {d.get('status')} | "
            f"{m.get('iou')} | {e.get('completeness_pct')} | {m.get('centroid_error')} | "
            f"{(r.get('manual_source') or {}).get('regenerated')} | "
            f"{d.get('qa31_ownership_conclusion_still_valid')} |"
        )
    lines += [
        "",
        "## Global",
        f"- Average IoU: {agg.get('average_iou')}",
        f"- Average completeness: {agg.get('average_completeness_pct')}",
        f"- Categories: {agg.get('category_counts')}",
        "",
    ]
    return "\n".join(lines)


def _recs_md(recs: Dict[str, Any], agg: Dict[str, Any]) -> str:
    lines = [
        f"# {PHASE_ID} Engineering Recommendations",
        "",
        "Based ONLY on collected evidence. No engineering modules modified.",
        "",
        f"Summary: {recs.get('summary')}",
        "",
    ]
    for pr in recs.get("priorities") or []:
        lines.append(f"## Priority {pr.get('priority')}: {pr.get('title')}")
        lines.append("")
        lines.append(pr.get("recommendation") or "")
        lines.append("")
        lines.append(f"Evidence: `{pr.get('evidence')}`")
        lines.append("")
    return "\n".join(lines)


def _readme_md(meta: Dict[str, Any], agg: Dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# Phase {PHASE_ID} — Ground Truth Crop Verification",
            "",
            f"MODEL_VERSION: `{MODEL_VERSION}`",
            "",
            "Diagnostic-only validation of Manual Beam Comparison Crops used in QA.3.0.",
            "",
            "## Constraints",
            "- No engineering / ownership / rendering / crop / estimation changes",
            "- Read-only consumption of QA.3.0 / Track1 artefacts",
            "",
            "## Key paths",
            f"- Drawing set: `{meta.get('drawing_set')}`",
            f"- Run root: `{meta.get('run_root')}`",
            f"- Reinforcement DXF: `{meta.get('reinforcement_dxf')}`",
            "",
            "## Headline result",
            f"- Categories A/B/C: `{agg.get('category_counts')}`",
            f"- Dominant finding: `{agg.get('dominant_finding')}`",
            f"- Baseline trustworthy: `{agg.get('baseline_trustworthy')}`",
            "",
            "See `ExecutionSummary.md` and `GroundTruthDecisionMatrix.json`.",
            "",
        ]
    )
