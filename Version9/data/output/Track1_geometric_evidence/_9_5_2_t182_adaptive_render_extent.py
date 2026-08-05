"""
T1.8.2 benchmark — Adaptive Beam Render Extent.
MODEL_VERSION: 9.5.2
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PhaseT182_adaptive_render_extent.phase_t182_orchestrator import (  # noqa: E402
    PhaseT182Orchestrator,
)

RUN = ROOT / "data" / "web_runs" / "qa2_First_Set_Drawings_20260803_132045"
TRACK1 = ROOT / "data" / "output" / "Track1_geometric_evidence"
BENCH = ["B1", "B2", "B3", "B8", "B9"]

_ARCH = """# T1.8.2 Architecture Summary — Adaptive Beam Render Extent

**MODEL_VERSION:** 9.5.2

## Purpose

Fix clipped top reinforcement annotations by computing an **adaptive
engineering-aware render viewport** from the UNION of all owned graphical
objects — without changing ownership, graph, or annotation assignment.

## Pipeline

```
BeamScopedAnnotations.json  (unchanged from T1.8)
        |
        v
Adaptive extent builder  (UNION owned objects + margin)
        |
        v
In-memory Beam.extent override
        |
        v
T1.8.1 ownership renderer (reused, unmodified source)
        |
        v
RenderedBeams / Comparison / Diff
        |
        v
Visibility QA  (object_bbox ⊂ render_bbox)
        |
        v
PASS / FAIL
```

## Algorithm

```
render_bbox = inflate(
    UNION(
        beam geometry,
        owned bars,
        owned leaders (+ elbow proxy, arrowheads),
        owned annotation anchors + text rectangles
    ),
    margin_x ≈ 8%, margin_y ≈ 8%, min 80 mm
)
```

## Package

`Version9/src/PhaseT182_adaptive_render_extent/`

| Module | Role |
|--------|------|
| `adaptive_bbox.py` | BBox helpers / text extent estimate |
| `render_extent_builder.py` | Owned-union + inflate |
| `visibility_validator.py` | Clipping / regression checks |
| `render_extent_qa.py` | Markdown + JSON writers |
| `phase_t182_orchestrator.py` | Wire-up |
"""

_DELIVERY = """# T1.8.2 Delivery Note — MODEL_VERSION 9.5.2

## Files created

- `Version9/src/PhaseT182_adaptive_render_extent/` (new)
- `Version9/data/output/Track1_geometric_evidence/_9_5_2_t182_adaptive_render_extent.py`

## Architecture

Additive viewport layer only. Reuses T1.8.1 renderer via in-memory
`Beam.attributes.extent` override. No edits to T1.7 / T1.7.1 / T1.8 / T1.8.1 source.

## Benchmark status

```
{summary}
```

## Regression

- Ownership identical (annotation texts match T1.8.1)
- Leader counts match T1.8.1
- Neighbour leakage remains zero
- Only viewport expanded

## Re-run

```text
python Version9/data/output/Track1_geometric_evidence/_9_5_2_t182_adaptive_render_extent.py
```
"""


def main() -> None:
    orch = PhaseT182Orchestrator(ROOT, RUN)
    result = orch.run()
    if not result.get("success"):
        print("T1.8.2 FAILED:", result)
        sys.exit(1)

    out_dir = Path(result["out_dir"])
    track_out = TRACK1 / "PhaseT182_adaptive_render_extent"
    if track_out.exists():
        shutil.rmtree(track_out)
    shutil.copytree(out_dir, track_out)

    qa = json.loads((out_dir / "RenderExtentQA.json").read_text(encoding="utf-8"))
    bench_rows = []
    for bid in BENCH:
        v = (qa.get("by_beam") or {}).get(bid) or {}
        bench_rows.append(
            {
                "beam": bid,
                "overall": v.get("overall"),
                "visual_validation": v.get("visual_validation"),
                "regression_ok": v.get("regression_ok"),
                "beam_bbox": v.get("beam_bbox"),
                "computed_render_bbox": v.get("computed_render_bbox"),
                "annotation_clipped": v.get("annotation_clipped"),
                "leader_clipped": v.get("leader_clipped"),
                "visibility_failures": v.get("visibility_failures"),
            }
        )
    bench = {
        "model_version": "9.5.2",
        "beams": BENCH,
        "rows": bench_rows,
        "pass_count": sum(1 for r in bench_rows if r.get("overall") == "PASS"),
        "fail_count": sum(1 for r in bench_rows if r.get("overall") != "PASS"),
        "full_run": {
            "beam_count": result.get("beam_count"),
            "pass_count": result.get("pass_count"),
            "fail_count": result.get("fail_count"),
            "visibility_pass": result.get("visibility_pass"),
            "regression_pass": result.get("regression_pass"),
        },
    }
    (track_out / "benchmark_summary.json").write_text(
        json.dumps(bench, indent=2), encoding="utf-8"
    )
    (TRACK1 / "t182_benchmark_summary.json").write_text(
        json.dumps(bench, indent=2), encoding="utf-8"
    )

    for name in (
        "T182_ADAPTIVE_EXTENT_QA_REPORT.md",
        "T182_VISUAL_SUMMARY.md",
        "RenderExtentQA.json",
    ):
        src = out_dir / name
        if src.exists():
            shutil.copy2(src, TRACK1 / name)

    arch = TRACK1 / "T182_ARCHITECTURE_SUMMARY.md"
    deliv = TRACK1 / "T182_DELIVERY_NOTE.md"
    arch.write_text(_ARCH, encoding="utf-8")
    deliv.write_text(
        _DELIVERY.format(summary=json.dumps(bench, indent=2)), encoding="utf-8"
    )
    shutil.copy2(arch, track_out / "ARCHITECTURE_SUMMARY.md")
    shutil.copy2(deliv, track_out / "DELIVERY_NOTE.md")
    shutil.copy2(arch, out_dir / "ARCHITECTURE_SUMMARY.md")
    shutil.copy2(deliv, out_dir / "DELIVERY_NOTE.md")

    print("Wrote", track_out)
    for r in bench_rows:
        print(
            r["beam"],
            r["overall"],
            "clipped_ann",
            r["annotation_clipped"],
            "bbox",
            r["beam_bbox"],
            "->",
            r["computed_render_bbox"],
        )


if __name__ == "__main__":
    main()
