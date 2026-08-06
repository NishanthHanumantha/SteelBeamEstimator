"""
T1.8 — QA diagnostics writer.
MODEL_VERSION: 9.5.0
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

MODEL_VERSION = "9.5.0"


def write_qa_report(
    dest: Path,
    *,
    rows: List[Dict[str, Any]],
    generated_at: str,
    out_dir: Path,
) -> Path:
    md: List[str] = []
    md.append("# T1.8 Beam Ownership Envelope QA Report")
    md.append("")
    md.append(f"**MODEL_VERSION:** {MODEL_VERSION}")
    md.append(f"**Generated:** {generated_at}")
    md.append("")
    md.append("## Principle")
    md.append("")
    md.append(
        "Filter T1.7 Annotation Graph chains through a deterministic "
        "**Beam Ownership Envelope** (engineering zone — not the crop window). "
        "Annotations inherit ownership only via Leader→PhysicalBar (or DESCRIBES "
        "owned bar); neighbour-row leakage is rejected by vertical ownership."
    )
    md.append("")
    md.append("## Benchmark summary")
    md.append("")
    md.append(
        "| Beam | Accepted | Rejected | Leakage | Top | Bottom | SideFace | Ld | "
        "Stirrup | Cross-beam rej | PASS/FAIL |"
    )
    md.append(
        "|------|---------:|---------:|--------:|:---:|:------:|:--------:|:--:|"
        ":-------:|---------------:|:---------:|"
    )
    for r in rows:
        o = r["ownership"]
        v = r["validation"]
        st = o.get("stats") or {}
        la = v.get("labels_accepted") or {}
        md.append(
            f"| **{o['beam']}** | {st.get('accepted_annotation_count')} | "
            f"{st.get('rejected_annotation_count')} | {v.get('leakage_count')} | "
            f"{'Y' if la.get('top_bars') or la.get('bottom_bars') else 'N'} | "
            f"{'Y' if la.get('bottom_bars') or la.get('top_bars') else 'N'} | "
            f"{'Y' if la.get('side_face') else '—'} | "
            f"{'Y' if la.get('ld') else '—'} | "
            f"{'Y' if la.get('stirrups') else 'N'} | "
            f"{st.get('cross_beam_leakage_count')} | "
            f"**{v.get('validation')}** |"
        )
    md.append("")
    for r in rows:
        o = r["ownership"]
        v = r["validation"]
        md.append(f"### {o['beam']}")
        md.append("")
        env = o.get("envelope") or {}
        ce = env.get("concrete_envelope") or {}
        md.append(
            f"- Body Y: `[{ce.get('y0')}, {ce.get('y1')}]` "
            f"side={env.get('side_of_mark')} reason={env.get('body_reason')}"
        )
        md.append(f"- Accepted: `{v.get('accepted_texts')}`")
        md.append(f"- Rejected: `{v.get('rejected_texts')}`")
        md.append("#### Rejected chains")
        md.append("")
        md.append("| Text | Reason | Rule | Neighbour hint |")
        md.append("|------|--------|------|----------------|")
        for c in o.get("rejected_chains") or []:
            md.append(
                f"| {c.get('text')} | {c.get('ownership_reason')} | "
                f"{c.get('rejected_rule')} | {c.get('neighbour_beam_source')} |"
            )
        md.append("")
        md.append(f"- Validation: **{v.get('validation')}** checks=`{v.get('checks')}`")
        md.append("")
    md.append("## Non-goals")
    md.append("")
    md.append("- No modifications to R.1 / R.3 / R.3.1 / T1.5–T1.7.1 / renderers")
    md.append("- No OCR / Vision / OpenCV / ML / LLM")
    md.append("")
    md.append(f"## Artefacts: `{out_dir}`")
    md.append("")
    md.append("- `BeamOwnership.json`")
    md.append("- `BeamScopedAnnotations.json`")
    md.append("- `OwnershipDiagnostics.json`")
    md.append("")
    dest.write_text("\n".join(md), encoding="utf-8")
    return dest
