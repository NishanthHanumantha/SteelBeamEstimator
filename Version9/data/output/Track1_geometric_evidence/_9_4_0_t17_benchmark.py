"""
T1.7 benchmark — Annotation Graph for B1/B2/B8/B9/B10.

Produces PhaseT17_annotation_graph under the web run + Track1 mirror/QA.
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PhaseT17_annotation_graph.phase_t17_orchestrator import (  # noqa: E402
    PhaseT17Orchestrator,
)
from PhaseT17_annotation_graph.graph_models import AnnotationGraph  # noqa: E402
from PhaseT17_annotation_graph.qa_diagnostics import diagnose_graph  # noqa: E402

RUN = ROOT / "data" / "web_runs" / "qa2_First_Set_Drawings_20260803_132045"
TRACK1 = ROOT / "data" / "output" / "Track1_geometric_evidence"
BENCH = ["B1", "B2", "B8", "B9", "B10"]


def main() -> None:
    orch = PhaseT17Orchestrator(ROOT, RUN)
    # Build for all envelope beams so shared leaders resolve consistently;
    # QA focuses on benchmark set.
    result = orch.run()
    if not result.get("success"):
        print("T1.7 FAILED:", result)
        sys.exit(1)

    out_dir = Path(result["out_dir"])
    track_out = TRACK1 / "PhaseT17_annotation_graph"
    if track_out.exists():
        shutil.rmtree(track_out)
    shutil.copytree(out_dir, track_out)

    graph = AnnotationGraph.from_dict(
        json.loads((out_dir / "AnnotationGraph.json").read_text(encoding="utf-8"))
    )
    qa = diagnose_graph(graph, BENCH)

    rows = []
    for bid in BENCH:
        d = qa["by_beam"][bid]
        flags = d["validation_flags"]
        rows.append(
            {
                "beam_id": bid,
                "physical_bars": d["physical_bars"],
                "leaders": d["leader_count"],
                "annotations": d["annotation_count"],
                "semantics": d["semantic_count"],
                "semantic_types": d["semantic_types"],
                "unresolved_leaders": d["unresolved_leader_count"],
                "unattached_annotations": d["unattached_annotation_count"],
                "dangling": d["dangling_count"],
                "components": d["disconnected_components"],
                "completeness_pct": d["graph_completeness_pct"],
                "leader_bar_chains": d["leader_bar_chains"],
                "has_top_bar_callout": flags["has_top_bar_callout"],
                "has_side_face": flags["has_side_face"],
                "has_ld": flags["has_ld"],
                "has_stirrup": flags["has_stirrup"],
                "has_multi_leader_chain": flags["has_multi_leader_chain"],
                "annotation_texts": d["annotation_texts"],
                "api_semantics": [
                    {
                        "type": n["type"],
                        "meaning": (n.get("attributes") or {}).get(
                            "engineering_meaning"
                        ),
                        "text": (n.get("attributes") or {}).get("raw_text"),
                    }
                    for n in graph.get_semantic_annotations(bid)
                ],
            }
        )

    bench_qa = {
        "phase_id": "T1.7",
        "model_version": result.get("model_version"),
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "benchmark_beams": BENCH,
        "run_summary": result,
        "rows": rows,
    }
    (track_out / "benchmark_qa.json").write_text(
        json.dumps(bench_qa, indent=2), encoding="utf-8"
    )
    (TRACK1 / "t17_benchmark_qa.json").write_text(
        json.dumps(bench_qa, indent=2), encoding="utf-8"
    )

    md = []
    md.append("# T1.7 Annotation Graph Resolver QA Report")
    md.append("")
    md.append(f"**MODEL_VERSION:** {bench_qa['model_version']}")
    md.append(f"**Generated:** {bench_qa['generated_at']}")
    md.append(f"**Run:** `{RUN.name}`")
    md.append("")
    md.append("## Principle")
    md.append("")
    md.append(
        "Build a deterministic engineering Annotation Graph "
        "(Beam → PhysicalBar → Leader → Annotation → Semantic). "
        "This phase does **not** modify rendering, OCR, Vision, or prior "
        "R.3 / R.3.1 / T1.5 / T1.6 logic."
    )
    md.append("")
    md.append("## Graph totals")
    md.append("")
    md.append(f"- Nodes: **{result.get('node_count')}**")
    md.append(f"- Edges: **{result.get('edge_count')}**")
    md.append(f"- Beams: **{result.get('beam_count')}**")
    md.append("")
    md.append("## Benchmark table")
    md.append("")
    md.append(
        "| Beam | Bars | Leaders | Anns | Semantics | Unres. LDR | "
        "Unatt. ANN | Completeness % | Chains | TopBar | SideFace | Ld | Stirrup |"
    )
    md.append(
        "|------|-----:|--------:|-----:|----------:|-----------:|"
        "-----------:|---------------:|-------:|:------:|:--------:|:--:|:--------:|"
    )
    for r in rows:
        md.append(
            f"| **{r['beam_id']}** | {r['physical_bars']} | {r['leaders']} | "
            f"{r['annotations']} | {r['semantics']} | {r['unresolved_leaders']} | "
            f"{r['unattached_annotations']} | {r['completeness_pct']} | "
            f"{r['leader_bar_chains']} | "
            f"{'Y' if r['has_top_bar_callout'] else 'N'} | "
            f"{'Y' if r['has_side_face'] else 'N'} | "
            f"{'Y' if r['has_ld'] else 'N'} | "
            f"{'Y' if r['has_stirrup'] else 'N'} |"
        )
    md.append("")
    md.append("## Missing-annotation recovery (manual checklist)")
    md.append("")
    for r in rows:
        md.append(f"### {r['beam_id']}")
        md.append("")
        md.append(f"- R.1 texts: `{r['annotation_texts']}`")
        md.append(f"- Semantic types: `{r['semantic_types']}`")
        md.append(
            f"- Validation: top_bar={r['has_top_bar_callout']}, "
            f"side_face={r['has_side_face']}, Ld={r['has_ld']}, "
            f"stirrup={r['has_stirrup']}, multi_leader_chain={r['has_multi_leader_chain']}"
        )
        md.append("")
    md.append("## Renderer contract (API)")
    md.append("")
    md.append("```")
    md.append("graph.get_beam_annotations(beam_id)")
    md.append("graph.get_physical_bars(beam_id)")
    md.append("graph.get_render_entities(beam_id)")
    md.append("graph.get_semantic_annotations(beam_id)")
    md.append("```")
    md.append("")
    md.append("## Artefacts")
    md.append("")
    md.append(f"- Run: `{out_dir}`")
    md.append(f"- Track1 mirror: `{track_out}`")
    md.append("- `AnnotationGraph.json`, `annotation_graph_by_beam.json`")
    md.append("- `graph_qa_diagnostics.json`, `graph_api_snapshot.json`")
    md.append("")
    md.append("## Non-goals confirmed")
    md.append("")
    md.append("- No OCR / Vision / OpenCV / ML / LLM")
    md.append("- No renderer rewrite")
    md.append("- No regression to R.3 / PhysicalBars / T1.6 ownership engines")
    md.append("")

    body = "\n".join(md)
    (track_out / "QA_REPORT.md").write_text(body, encoding="utf-8")
    (out_dir / "QA_REPORT.md").write_text(body, encoding="utf-8")
    (TRACK1 / "T17_ANNOTATION_GRAPH_QA_REPORT.md").write_text(body, encoding="utf-8")
    print("Wrote", track_out / "QA_REPORT.md")
    for r in rows:
        print(
            r["beam_id"],
            "bars",
            r["physical_bars"],
            "anns",
            r["annotations"],
            "sem",
            r["semantics"],
            "comp%",
            r["completeness_pct"],
            "Ld",
            r["has_ld"],
            "Side",
            r["has_side_face"],
            "chains",
            r["leader_bar_chains"],
        )


if __name__ == "__main__":
    main()
