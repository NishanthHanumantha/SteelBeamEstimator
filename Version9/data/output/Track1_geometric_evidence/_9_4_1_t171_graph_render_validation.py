"""
T1.7.1 benchmark — Graph-aware render validation for B1/B2/B8/B9/B10.
MODEL_VERSION: 9.4.1
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

from PhaseT171_graph_render_validation.phase_t171_orchestrator import (  # noqa: E402
    PhaseT171Orchestrator,
)

RUN = ROOT / "data" / "web_runs" / "qa2_First_Set_Drawings_20260803_132045"
TRACK1 = ROOT / "data" / "output" / "Track1_geometric_evidence"
BENCH = ["B1", "B2", "B8", "B9", "B10"]


def main() -> None:
    orch = PhaseT171Orchestrator(ROOT, RUN)
    result = orch.run(beam_ids=BENCH)
    if not result.get("success"):
        print("T1.7.1 FAILED:", result)
        sys.exit(1)

    out_dir = Path(result["out_dir"])
    track_out = TRACK1 / "PhaseT171_graph_render_validation"
    if track_out.exists():
        shutil.rmtree(track_out)
    shutil.copytree(out_dir, track_out)

    # Mirror key reports to Track1 root
    for name in (
        "T171_GRAPH_RENDER_VALIDATION_QA_REPORT.md",
        "Difference_Report.json",
        "validation_summary.json",
    ):
        src = track_out / name
        if src.exists():
            shutil.copy2(src, TRACK1 / name)

    # Architecture + delivery notes written beside Track1
    arch = TRACK1 / "T171_ARCHITECTURE_SUMMARY.md"
    deliv = TRACK1 / "T171_DELIVERY_NOTE.md"
    arch.write_text(_ARCH, encoding="utf-8")
    deliv.write_text(_DELIVERY.format(out=track_out, result=json.dumps(result.get("summary"), indent=2)), encoding="utf-8")
    shutil.copy2(arch, track_out / "ARCHITECTURE_SUMMARY.md")
    shutil.copy2(deliv, track_out / "DELIVERY_NOTE.md")
    shutil.copy2(arch, out_dir / "ARCHITECTURE_SUMMARY.md")
    shutil.copy2(deliv, out_dir / "DELIVERY_NOTE.md")

    print("Wrote", track_out)
    print("Overview PDF:", result.get("overview_pdf"))
    print("Summary:", result.get("summary"))


_ARCH = """# T1.7.1 Architecture Summary — Graph-Aware Render Validation

**MODEL_VERSION:** 9.4.1

## Purpose

Visual proof that the T1.7 Annotation Graph improves engineering renders.
Validation-only — no graph / ownership / prior-renderer changes.

## Package

`Version9/src/PhaseT171_graph_render_validation/`

| Module | Role |
|--------|------|
| `renderer_snapshot.py` | Locate/copy original crop (black-box regenerate if needed) |
| `graph_overlay_renderer.py` | Separate validation renderer: DXF base + graph overlays |
| `comparison_renderer.py` | Side-by-side + Difference_Report.json |
| `benchmark_validator.py` | PASS/FAIL checks |
| `qa_report.py` | Markdown QA with embedded gallery refs |
| `phase_t171_orchestrator.py` | End-to-end wire-up |

## Pipeline

```
Existing Renderer ──► Original_Render.png
AnnotationGraph   ──► Graph Overlay Renderer ──► GraphAware / Overlay
                              │
                              ▼
                    SideBySide + Difference_Report
                              │
                              ▼
                    ValidationGallery + Overview.pdf + QA
```

## Overlay colours

- Physical Bar — green
- Leader — blue
- Annotation — orange
- Semantic — purple
- Chain — red dotted
- Beam envelope — grey dashed
"""

_DELIVERY = """# T1.7.1 Delivery Note — MODEL_VERSION 9.4.1

## Delivered

1. Package `PhaseT171_graph_render_validation`
2. Validation outputs: `{out}`
3. `ValidationGallery/` with B*_Comparison.png + Overview.pdf
4. Per-beam Original / GraphAware / Overlay / SideBySide / Difference_Report
5. `T171_GRAPH_RENDER_VALIDATION_QA_REPORT.md`

## Summary

```
{result}
```

## Re-run

```text
python Version9/data/output/Track1_geometric_evidence/_9_4_1_t171_graph_render_validation.py
```

## Regression

- T1.7 AnnotationGraph not modified
- Existing dxf_renderer / T1.6 ownership renderer not modified
- No OCR / OpenCV / Vision / ML / LLM
"""


if __name__ == "__main__":
    main()
