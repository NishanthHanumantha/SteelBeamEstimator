"""
9.3.3 R1/R3 risk check — report every beam whose padding was shrunk or
zeroed due to a close neighbor, across all 3 sets' full annotation scope
(not just the residual/OpenCV target beams), so R1 (padding-too-tight)
and R3 (adjacent-beam-bleed) are backed by evidence rather than assertion.

Read-only: does not modify beam_extent.py or any detection code.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # Version9
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import ezdxf  # noqa: E402

from PhaseT1_geometric_stirrup_evidence.beam_extent import (  # noqa: E402
    compute_extents_for_beams,
)

WEB_RUNS = ROOT / "data" / "web_runs"
SETS = {
    "Set1": "qa2_First_Set_Drawings_20260803_132045",
    "Set2": "qa2_Second_Set_Drawings_20260803_132207",
    "Set3": "qa2_Third_Set_Drawings_20260803_132502",
}


def _find_reinforcement_dxf(run_root: Path) -> Path:
    for p in run_root.rglob("*.dxf"):
        if "reinforc" in p.name.lower() or "stirrup" in p.name.lower():
            return p
    raise FileNotFoundError(f"no reinforcement dxf found under {run_root}")


def main() -> None:
    report = {"sets": {}}
    for set_id, run_name in SETS.items():
        run_root = WEB_RUNS / run_name
        dxf = _find_reinforcement_dxf(run_root)
        doc = ezdxf.readfile(str(dxf))
        msp = doc.modelspace()

        ann_path = (
            run_root / "data" / "output" / "PhaseR.1_generalized_reinforcement_discovery"
            / "reinforcement_annotations.json"
        )
        anns = json.loads(ann_path.read_text(encoding="utf-8"))
        annotations_by_beam = anns.get("by_beam") or {}

        extents = compute_extents_for_beams(
            list(annotations_by_beam.keys()), annotations_by_beam, msp
        )

        tightened = []
        for bid, info in extents.items():
            notes = info.get("notes") or []
            real_notes = [n for n in notes if n != "no_annotations_for_beam"]
            if real_notes:
                tightened.append({
                    "beam_id": bid,
                    "pad_used_mm": info.get("pad_used_mm"),
                    "notes": real_notes,
                })

        report["sets"][set_id] = {
            "total_beams_with_extent": sum(
                1 for v in extents.values() if v.get("extent") is not None
            ),
            "beams_with_padding_tightened": len(tightened),
            "details": tightened,
        }

    out = ROOT / "data" / "output" / "Track1_geometric_evidence" / "r1_r3_padding_evidence.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
