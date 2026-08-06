"""
T1.7.1 — Engineering QA report writer.
MODEL_VERSION: 9.4.1
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

MODEL_VERSION = "9.4.1"


def write_qa_report(
    *,
    dest: Path,
    rows: List[Dict[str, Any]],
    out_dir: Path,
    gallery_dir: Path,
    generated_at: str,
) -> Path:
    dest = Path(dest)
    md: List[str] = []
    md.append("# T1.7.1 Graph-Aware Render Validation QA Report")
    md.append("")
    md.append(f"**MODEL_VERSION:** {MODEL_VERSION}")
    md.append(f"**Generated:** {generated_at}")
    md.append("")
    md.append("## Purpose")
    md.append("")
    md.append(
        "Prove — with deterministic visual evidence — that the T1.7 Annotation "
        "Graph improves the engineering rendering consumed by downstream "
        "Vision/LLM modules. This phase does **not** modify graph generation "
        "or existing renderers."
    )
    md.append("")
    md.append("## Pipeline")
    md.append("")
    md.append("```")
    md.append("Existing Renderer → Original_Render.png")
    md.append("AnnotationGraph  → Graph Overlay Renderer → GraphAware / Overlay")
    md.append("                        ↓")
    md.append("              SideBySide.png + Difference_Report.json")
    md.append("                        ↓")
    md.append("                   Engineering QA")
    md.append("```")
    md.append("")
    md.append("## Benchmark summary")
    md.append("")
    md.append(
        "| Beam | Orig anns | Graph anns | Newly visible | SideFace | Ld | "
        "Stirrup | TopBars | Chains | PASS/FAIL |"
    )
    md.append(
        "|------|----------:|-----------:|---------------|:--------:|:--:|"
        ":-------:|:-------:|-------:|:---------:|"
    )
    for r in rows:
        d = r["difference"]
        v = r["validation"]
        flags = d.get("flags") or {}
        md.append(
            f"| **{d['beam']}** | {d['original_annotations']} | "
            f"{d['graph_annotations']} | "
            f"{', '.join(d.get('newly_visible') or []) or '—'} | "
            f"{'Y' if flags.get('side_face') else '—'} | "
            f"{'Y' if flags.get('ld') else '—'} | "
            f"{'Y' if flags.get('stirrup') else 'N'} | "
            f"{'Y' if flags.get('top_bar_callout') else 'N'} | "
            f"{d.get('leader_bar_chains')} | "
            f"**{v.get('validation')}** |"
        )
    md.append("")
    md.append("## Per-beam visual evidence")
    md.append("")
    for r in rows:
        bid = r["difference"]["beam"]
        md.append(f"### {bid}")
        md.append("")
        side = gallery_dir / f"{bid}_Comparison.png"
        # relative-ish paths for report location
        md.append(f"- Side-by-side: `{side}`")
        md.append(f"- Beam folder: `{out_dir / bid}`")
        md.append(
            f"- Newly recovered: `{r['difference'].get('newly_visible')}`"
        )
        md.append(
            f"- Validation: **{r['validation'].get('validation')}** "
            f"(checks={r['validation'].get('checks')})"
        )
        # Embed relative image if gallery is sibling
        rel = f"ValidationGallery/{bid}_Comparison.png"
        md.append("")
        md.append(f"![{bid} comparison]({rel})")
        md.append("")
    md.append("## Overlay colour legend")
    md.append("")
    md.append("| Element | Colour |")
    md.append("|---------|--------|")
    md.append("| Physical Bar | Green `#2ECC71` |")
    md.append("| Leader / tip | Blue / teal |")
    md.append("| Annotation | Orange `#E67E22` |")
    md.append("| Semantic | Purple `#9B59B6` |")
    md.append("| Ann→Leader chain | Red dotted |")
    md.append("| Beam envelope | Grey dashed |")
    md.append("")
    md.append("## Regression confirmation")
    md.append("")
    md.append("- R.1 / R.3 / R.3.1 / T1.5 / T1.6 / T1.7 **not modified**")
    md.append("- Existing DXF renderer used as black-box only")
    md.append("- Separate validation renderer in `PhaseT171_graph_render_validation`")
    md.append("- No OCR / OpenCV / Vision / ML / LLM")
    md.append("")
    md.append("## Artefacts")
    md.append("")
    md.append(f"- Output root: `{out_dir}`")
    md.append(f"- Gallery: `{gallery_dir}`")
    md.append("- Per beam: `Original_Render.png`, `GraphAware_Render.png`, "
              "`Overlay_Render.png`, `SideBySide.png`, `Difference_Report.json`")
    md.append("- `Overview.pdf` in ValidationGallery")
    md.append("")

    dest.write_text("\n".join(md), encoding="utf-8")
    return dest
