"""
9.3.3 Part A2 — line-weight validation at the NEW local-extent crop
resolution, reusing T1.1's exact methodology (renderer_validation.py
check (c): scan every ~1/40th row, measure contiguous ink-run lengths
1-12px, report min/median run width). Applied to the TEST SET's
regenerated {beam_id}_crop.png (text ON) files instead of the full
6000x4400 sheet render, to confirm thin stirrup-tick geometry survives
at the new fixed target resolution.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]  # Version9
RENDER_DIR = (
    ROOT
    / "data"
    / "web_runs"
    / "qa2_First_Set_Drawings_20260803_132045"
    / "data"
    / "output"
    / "PhaseT1_geometric_stirrup_evidence"
    / "opencv_renders"
)
# B1 is accepted by T1.2 vector detection in the production run (no OpenCV
# fallback crop generated there) -- its regenerated 9.3.3 local-extent crop
# instead lives under the standalone Part C test output (_local_crop_test.py).
FALLBACK_RENDER_DIR = (
    ROOT / "data" / "output" / "PhaseT1_geometric_stirrup_evidence" / "opencv_renders"
)
TEST_BEAMS = ["B1", "B2", "B8", "B9", "B10"]


def line_weight_check(png_path: Path) -> dict:
    img = np.array(Image.open(png_path).convert("L"))
    ink = img < 250
    h, w = ink.shape
    widths = []
    for row in range(0, h, max(1, h // 40)):
        run = 0
        for col in range(w):
            if ink[row, col]:
                run += 1
            elif run:
                if 1 <= run <= 12:
                    widths.append(run)
                run = 0
    min_w = min(widths) if widths else None
    med_w = sorted(widths)[len(widths) // 2] if widths else None
    return {
        "pass": bool(min_w is not None and int(min_w) >= 1),
        "img_size": [int(w), int(h)],
        "min_measured_ink_run_px": int(min_w) if min_w is not None else None,
        "median_thin_run_px": int(med_w) if med_w is not None else None,
        "samples": int(len(widths)),
    }


def main() -> None:
    report = {}
    for bid in TEST_BEAMS:
        p = RENDER_DIR / f"{bid}_crop.png"
        source = "production_orchestrator_run"
        if not p.exists():
            p = FALLBACK_RENDER_DIR / f"Set1_{bid}_crop.png"
            source = "part_c_standalone_test"
        if not p.exists():
            report[bid] = {"pass": False, "error": "crop png missing"}
            continue
        row = line_weight_check(p)
        row["source"] = source
        report[bid] = row

    out = ROOT / "data" / "output" / "Track1_geometric_evidence" / "part_a2_crop_line_weight.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
