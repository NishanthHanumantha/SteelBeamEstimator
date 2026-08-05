"""
T1.8 benchmark — Beam Ownership Envelope for B1/B2/B8/B9/B10.
MODEL_VERSION: 9.5.0
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

from PhaseT18_beam_ownership.phase_t18_orchestrator import (  # noqa: E402
    PhaseT18Orchestrator,
)

RUN = ROOT / "data" / "web_runs" / "qa2_First_Set_Drawings_20260803_132045"
TRACK1 = ROOT / "data" / "output" / "Track1_geometric_evidence"
BENCH = ["B1", "B2", "B8", "B9", "B10"]

_ARCH = """# T1.8 Architecture Summary — Beam Ownership Envelope Resolver

**MODEL_VERSION:** 9.5.0

## Purpose

Deterministically decide whether each T1.7 graph chain belongs to the active
beam. Fixes crop-scoped neighbour leakage (e.g. B5 `2-Y12` / `2150` into B1).

## Position

```
T1.7 AnnotationGraph
        |
        v
T1.8 Beam Ownership Envelope Resolver   <-- NEW (additive)
        |
        v
BeamScopedAnnotations.json  --> future graph-aware render / Vision
```

Does **not** modify T1.7, T1.7.1, T1.6, R.3.x, or renderers.

## Package

`Version9/src/PhaseT18_beam_ownership/`

| Module | Role |
|--------|------|
| `beam_envelope.py` | Engineering ownership zone (not crop) |
| `ownership_rules.py` | R1–R10 explicit rules |
| `ownership_filter.py` | Chain filter → BeamOwnership |
| `ownership_validator.py` | Benchmark PASS/FAIL |
| `qa_diagnostics.py` | QA markdown |
| `phase_t18_orchestrator.py` | Wire-up |

## Ownership envelope

Per beam: concrete body, top/bottom zones, stirrup region, side-face web,
annotation reach (same side of mark as body), support / Ld extensions.

Vertical rule: PhysicalBar Y must lie in the beam reinforcement elevation
cluster nearest the beam's annotation cloud — never the stacked neighbour row.
"""

_DELIVERY = """# T1.8 Delivery Note — MODEL_VERSION 9.5.0

## Delivered

1. Package `PhaseT18_beam_ownership`
2. `BeamOwnership.json`, `BeamScopedAnnotations.json`, `OwnershipDiagnostics.json`
3. `T18_BEAM_OWNERSHIP_QA_REPORT.md`
4. Benchmark runner `_9_5_0_t18_beam_ownership.py`

## Summary

```
{summary}
```

## Re-run

```text
python Version9/data/output/Track1_geometric_evidence/_9_5_0_t18_beam_ownership.py
```

## Regression

- T1.7 AnnotationGraph unchanged
- T1.7.1 validation renderer unchanged
- No OCR / Vision / OpenCV / ML / LLM
"""


def main() -> None:
    orch = PhaseT18Orchestrator(ROOT, RUN)
    # Full envelope set for consistency; QA focuses on BENCH
    result = orch.run()
    if not result.get("success"):
        print("T1.8 FAILED:", result)
        sys.exit(1)

    out_dir = Path(result["out_dir"])
    track_out = TRACK1 / "PhaseT18_beam_ownership"
    if track_out.exists():
        shutil.rmtree(track_out)
    shutil.copytree(out_dir, track_out)

    # Bench-focused summary
    own = json.loads((out_dir / "BeamOwnership.json").read_text(encoding="utf-8"))
    diag = json.loads(
        (out_dir / "OwnershipDiagnostics.json").read_text(encoding="utf-8")
    )
    bench_rows = []
    for bid in BENCH:
        o = own["by_beam"][bid]
        v = diag["by_beam"][bid]["validation"]
        bench_rows.append(
            {
                "beam": bid,
                "accepted": [a.get("text") for a in o["accepted_annotations"]],
                "rejected": [a.get("text") for a in o["rejected_annotations"]],
                "leakage": v.get("leakage_count"),
                "validation": v.get("validation"),
                "checks": v.get("checks"),
                "envelope_body": o["envelope"]["concrete_envelope"],
                "side": o["envelope"]["side_of_mark"],
            }
        )
    bench = {
        "model_version": "9.5.0",
        "beams": BENCH,
        "rows": bench_rows,
        "pass_count": sum(1 for r in bench_rows if r["validation"] == "PASS"),
        "fail_count": sum(1 for r in bench_rows if r["validation"] != "PASS"),
    }
    (track_out / "benchmark_summary.json").write_text(
        json.dumps(bench, indent=2), encoding="utf-8"
    )
    (TRACK1 / "t18_benchmark_summary.json").write_text(
        json.dumps(bench, indent=2), encoding="utf-8"
    )

    for name in (
        "T18_BEAM_OWNERSHIP_QA_REPORT.md",
        "BeamOwnership.json",
        "BeamScopedAnnotations.json",
    ):
        src = track_out / name
        if src.exists() and name.endswith(".md"):
            shutil.copy2(src, TRACK1 / name)

    arch = TRACK1 / "T18_ARCHITECTURE_SUMMARY.md"
    deliv = TRACK1 / "T18_DELIVERY_NOTE.md"
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
            r["validation"],
            "acc",
            r["accepted"],
            "rej",
            r["rejected"],
        )


if __name__ == "__main__":
    main()
