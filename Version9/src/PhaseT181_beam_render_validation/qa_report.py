"""
T1.8.1 — Markdown QA report generator.
MODEL_VERSION: 9.5.1
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

MODEL_VERSION = "9.5.1"


def write_qa_report(
    dest: Path,
    *,
    rows: List[Dict[str, Any]],
    generated_at: str,
    out_dir: Path,
) -> None:
    lines = [
        "# T1.8.1 — Beam Ownership Render Validation QA Report",
        "",
        f"**MODEL_VERSION:** {MODEL_VERSION}",
        f"**Generated:** {generated_at}",
        f"**Output:** `{out_dir}`",
        "",
        "Visual validation of T1.8 `BeamScopedAnnotations.json` against manual AutoCAD crops.",
        "Ownership logic is **not** modified — this phase is a consumer only.",
        "",
        "## Summary",
        "",
        f"- Beams: {len(rows)}",
        f"- PASS: {sum(1 for r in rows if r['validation']['visual_validation'] == 'PASS')}",
        f"- FAIL: {sum(1 for r in rows if r['validation']['visual_validation'] != 'PASS')}",
        "",
        "---",
        "",
    ]
    for r in rows:
        v = r["validation"]
        bid = v["beam"]
        lines.extend(
            [
                f"## Beam : {bid}",
                "",
                f"- Manual image: `{v['artefacts'].get('manual')}`",
                f"- Rendered image: `{v['artefacts'].get('render')}`",
                f"- Side-by-side: `{v['artefacts'].get('side_by_side')}`",
                f"- Diff image: `{v['artefacts'].get('diff')}`",
                "",
                f"- Expected annotations: `{v['expected_annotations']}`",
                f"- Rendered annotations: `{v['rendered_annotations']}`",
                f"- Missing: `{v['missing_annotations']}`",
                f"- Extra: `{v['unexpected_annotations']}`",
                f"- Neighbour leak: `{v.get('neighbour_leak_annotations')}`",
                f"- Rejected (not rendered): `{v['rejected_annotation_count']}`",
                f"- Leaders rendered: `{v['rendered_leaders']}`",
                f"- Bars rendered: `{v['rendered_bars']}`",
                "",
                f"**{v['visual_validation']}**",
                "",
                "Checks:",
                "",
            ]
        )
        for k, ok in (v.get("checks") or {}).items():
            lines.append(f"- `{'PASS' if ok else 'FAIL'}` {k}")
        lines.extend(["", "---", ""])

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines), encoding="utf-8")


def write_visual_summary(
    dest: Path,
    *,
    rows: List[Dict[str, Any]],
    generated_at: str,
) -> None:
    lines = [
        "# T1.8.1 — Visual Summary",
        "",
        f"**MODEL_VERSION:** {MODEL_VERSION}",
        f"**Generated:** {generated_at}",
        "",
        "| Beam | Render | Comparison | Diff | Status |",
        "|------|--------|------------|------|--------|",
    ]
    for r in rows:
        v = r["validation"]
        bid = v["beam"]
        art = v.get("artefacts") or {}
        lines.append(
            f"| {bid} | `{Path(art.get('render') or '').name}` | "
            f"`{Path(art.get('side_by_side') or '').name}` | "
            f"`{Path(art.get('diff') or '').name}` | "
            f"**{v['visual_validation']}** |"
        )
    lines.append("")
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines), encoding="utf-8")
