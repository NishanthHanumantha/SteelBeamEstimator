"""
T1.8.2 — QA markdown / JSON writers.
MODEL_VERSION: 9.5.2
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

MODEL_VERSION = "9.5.2"


def write_render_extent_qa_json(dest: Path, by_beam: Dict[str, Any], generated_at: str) -> None:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "phase_id": "T1.8.2",
        "model_version": MODEL_VERSION,
        "generated_at": generated_at,
        "by_beam": by_beam,
    }
    dest.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def write_qa_report(
    dest: Path,
    *,
    rows: List[Dict[str, Any]],
    generated_at: str,
    out_dir: Path,
) -> None:
    lines = [
        "# T1.8.2 — Adaptive Beam Render Extent QA Report",
        "",
        f"**MODEL_VERSION:** {MODEL_VERSION}",
        f"**Generated:** {generated_at}",
        f"**Output:** `{out_dir}`",
        "",
        "Viewport-only enhancement. Ownership / graph / annotation assignment unchanged.",
        "",
        "## Summary",
        "",
        f"- Beams: {len(rows)}",
        f"- Visibility PASS: {sum(1 for r in rows if r['visibility']['visual_validation'] == 'PASS')}",
        f"- Visibility FAIL: {sum(1 for r in rows if r['visibility']['visual_validation'] != 'PASS')}",
        f"- Regression PASS: {sum(1 for r in rows if (r.get('regression') or {}).get('regression_ok'))}",
        "",
        "---",
        "",
    ]
    for r in rows:
        v = r["visibility"]
        bid = v["beam"]
        ext = r.get("extent") or {}
        reg = r.get("regression") or {}
        lines.extend(
            [
                f"## Beam : {bid}",
                "",
                f"- Beam bbox: `{ext.get('beam_bbox')}`",
                f"- Owned union bbox: `{ext.get('owned_union_bbox')}`",
                f"- Computed render bbox: `{ext.get('computed_render_bbox')}`",
                f"- Margin applied: `{ext.get('margin_applied')}`",
                f"- Largest margin used: `{ext.get('largest_margin_used')}`",
                "",
                f"- annotation_clipped: `{v.get('annotation_clipped')}`",
                f"- leader_clipped: `{v.get('leader_clipped')}`",
                f"- text_bbox_outside_image: `{v.get('text_bbox_outside_image')}`",
                f"- arrowhead_outside_image: `{v.get('arrowhead_outside_image')}`",
                f"- render_bbox_contains_all_owned_objects: `{v.get('render_bbox_contains_all_owned_objects')}`",
                f"- Visibility failures: `{v.get('visibility_failures')}`",
                f"- Objects touching border: `{v.get('objects_touching_border')}`",
                "",
                f"- Regression OK: `{reg.get('regression_ok')}`",
                f"- Annotations (T182): `{(r.get('render') or {}).get('rendered_annotation_texts')}`",
                "",
                f"**Visibility: {v.get('visual_validation')}**",
                "",
                "---",
                "",
            ]
        )
    Path(dest).write_text("\n".join(lines), encoding="utf-8")


def write_visual_summary(
    dest: Path,
    *,
    rows: List[Dict[str, Any]],
    generated_at: str,
) -> None:
    lines = [
        "# T1.8.2 — Visual Summary (Adaptive Extent)",
        "",
        f"**MODEL_VERSION:** {MODEL_VERSION}",
        f"**Generated:** {generated_at}",
        "",
        "| Beam | Render bbox expanded | Visibility | Regression | Status |",
        "|------|---------------------|------------|------------|--------|",
    ]
    for r in rows:
        v = r["visibility"]
        bid = v["beam"]
        ext = r.get("extent") or {}
        beam_bb = ext.get("beam_bbox")
        rend_bb = ext.get("computed_render_bbox")
        expanded = "n/a"
        if beam_bb and rend_bb:
            expanded = "YES" if (
                rend_bb[1] < beam_bb[1] - 1 or rend_bb[3] > beam_bb[3] + 1
                or rend_bb[0] < beam_bb[0] - 1 or rend_bb[2] > beam_bb[2] + 1
            ) else "NO"
        reg = (r.get("regression") or {}).get("regression_ok")
        overall = (
            "PASS"
            if v.get("visual_validation") == "PASS" and reg is not False
            else "FAIL"
        )
        lines.append(
            f"| {bid} | {expanded} | {v.get('visual_validation')} | "
            f"{'PASS' if reg else 'FAIL'} | **{overall}** |"
        )
    lines.append("")
    Path(dest).write_text("\n".join(lines), encoding="utf-8")
