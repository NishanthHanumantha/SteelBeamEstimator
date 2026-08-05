"""
T1.8.1 benchmark — Beam Ownership Render Validation.
MODEL_VERSION: 9.5.1
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

from PhaseT181_beam_render_validation.phase_t181_orchestrator import (  # noqa: E402
    PhaseT181Orchestrator,
)

RUN = ROOT / "data" / "web_runs" / "qa2_First_Set_Drawings_20260803_132045"
TRACK1 = ROOT / "data" / "output" / "Track1_geometric_evidence"
BENCH = ["B1", "B2", "B8", "B9", "B10"]

_ARCH = """# T1.8.1 Architecture Summary — Beam Ownership Render Validation

**MODEL_VERSION:** 9.5.1

## Purpose

Visual validation that T1.8 `BeamScopedAnnotations.json` renders as a
beam-scoped engineering view with **zero neighbour leakage**.

## Pipeline

```
BeamScopedAnnotations.json  (+ BeamOwnership.json)
        |
        v
Ownership Render Layer   (PhaseT181 — NEW, additive)
        |
        v
Rendered Beam PNG
        |
        +---- Manual AutoCAD crop (existing benchmark)
        |
        v
Comparison Engine  --> side_by_side.png
        |
        v
Diff Engine        --> diff.png
        |
        v
QA Report / Visual Summary / RenderValidation.json
        |
        v
PASS / FAIL
```

## Constraints

- Does **not** modify T1.7, T1.7.1, T1.8, ownership rules, or existing renderers
- DXF base via black-box `PhaseM.1` call with `render_text=False`
- Only owned annotations / leaders / bars are overlaid

## Package

`Version9/src/PhaseT181_beam_render_validation/`

| Module | Role |
|--------|------|
| `ownership_renderer.py` | Scoped-only render |
| `comparison_engine.py` | Side-by-side + pixel diff |
| `image_exporter.py` | Manual crop locate / DXF helpers |
| `validation_engine.py` | Structural PASS/FAIL |
| `qa_report.py` | Markdown QA + summary |
| `phase_t181_orchestrator.py` | Wire-up |
"""

_DELIVERY = """# T1.8.1 Delivery Note — MODEL_VERSION 9.5.1

## Files created

- `Version9/src/PhaseT181_beam_render_validation/` (new package)
- `Version9/data/output/Track1_geometric_evidence/_9_5_1_t181_render_validation.py`

## Architecture

Strictly additive consumer of T1.8 scoped annotations. Visual QA only.

## Benchmark status

```
{summary}
```

## Regression status

- T1.7 unchanged
- T1.7.1 unchanged
- T1.8 unchanged
- Renderer wrappers only (black-box DXF import)
- No ownership / graph / engineering rule modifications

## Outputs

`PhaseT181_render_validation/`

- `RenderedBeams/`
- `Comparison/`
- `Diff/`
- `QA/`
- `RenderValidation.json`
- `T181_RENDER_VALIDATION_QA_REPORT.md`
- `T181_VISUAL_SUMMARY.md`

## Re-run

```text
python Version9/data/output/Track1_geometric_evidence/_9_5_1_t181_render_validation.py
```
"""


def main() -> None:
    orch = PhaseT181Orchestrator(ROOT, RUN)
    # Full beam set for engineering evidence; bench summary focuses on BENCH
    result = orch.run()
    if not result.get("success"):
        print("T1.8.1 FAILED:", result)
        sys.exit(1)

    out_dir = Path(result["out_dir"])
    track_out = TRACK1 / "PhaseT181_render_validation"
    if track_out.exists():
        shutil.rmtree(track_out)
    shutil.copytree(out_dir, track_out)

    val_doc = json.loads(
        (out_dir / "RenderValidation.json").read_text(encoding="utf-8")
    )
    bench_rows = []
    for bid in BENCH:
        v = (val_doc.get("by_beam") or {}).get(bid) or {}
        bench_rows.append(
            {
                "beam": bid,
                "visual_validation": v.get("visual_validation"),
                "rendered_annotations": v.get("rendered_annotations"),
                "missing_annotations": v.get("missing_annotations"),
                "unexpected_annotations": v.get("unexpected_annotations"),
                "neighbour_leak_annotations": v.get("neighbour_leak_annotations"),
                "rendered_leaders": v.get("rendered_leaders"),
                "rendered_bars": v.get("rendered_bars"),
                "checks": v.get("checks"),
            }
        )
    bench = {
        "model_version": "9.5.1",
        "beams": BENCH,
        "rows": bench_rows,
        "pass_count": sum(
            1 for r in bench_rows if r.get("visual_validation") == "PASS"
        ),
        "fail_count": sum(
            1 for r in bench_rows if r.get("visual_validation") != "PASS"
        ),
        "full_run": {
            "beam_count": result.get("beam_count"),
            "pass_count": result.get("pass_count"),
            "fail_count": result.get("fail_count"),
        },
    }
    (track_out / "benchmark_summary.json").write_text(
        json.dumps(bench, indent=2), encoding="utf-8"
    )
    (TRACK1 / "t181_benchmark_summary.json").write_text(
        json.dumps(bench, indent=2), encoding="utf-8"
    )

    for name in (
        "T181_RENDER_VALIDATION_QA_REPORT.md",
        "T181_VISUAL_SUMMARY.md",
    ):
        src = out_dir / name
        if src.exists():
            shutil.copy2(src, TRACK1 / name)

    arch = TRACK1 / "T181_ARCHITECTURE_SUMMARY.md"
    deliv = TRACK1 / "T181_DELIVERY_NOTE.md"
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
            r["visual_validation"],
            "rendered",
            r["rendered_annotations"],
            "miss",
            r["missing_annotations"],
            "extra",
            r["unexpected_annotations"],
        )


if __name__ == "__main__":
    main()
