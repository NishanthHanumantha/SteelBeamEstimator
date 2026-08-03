"""
9.3.3 Part A/B/C — local-extent crop test on the fixed 5-beam TEST SET.

Purges stale Set1 B1/B2/B8/B9/B10 crop/notext PNGs, computes beam-scoped
extents (beam_extent.compute_extents_for_beams — reuses R.1's existing
annotation association, no re-derivation), renders NEW local-extent
text-on crop.png + text-off notext.png at a fixed resolution, and reports
old-vs-new pixel dimensions + notext ink density for the visual gate.

Read/render only — does not touch T1.2 detection, T1.3 fusion, or T1.4.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]  # Version9
SYS_SRC = ROOT / "src"
if str(SYS_SRC) not in sys.path:
    sys.path.insert(0, str(SYS_SRC))

import importlib.util

import ezdxf  # noqa: E402

from PhaseT1_geometric_stirrup_evidence.beam_extent import (  # noqa: E402
    compute_extents_for_beams,
)


def load_dxf_renderer():
    renderer_path = SYS_SRC / "PhaseM.1_engineering_vision_dataset" / "dxf_renderer.py"
    spec = importlib.util.spec_from_file_location("dxf_renderer_9_3_3", renderer_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["dxf_renderer_9_3_3"] = mod
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod.render_dxf_region_to_png

RUN_ROOT = ROOT / "data" / "web_runs" / "qa2_First_Set_Drawings_20260803_132045"
OUT_ROOT = RUN_ROOT / "data" / "output"
CROP_DIR = ROOT / "data" / "output" / "PhaseT1_geometric_stirrup_evidence" / "opencv_renders"
TEST_BEAMS = ["B1", "B2", "B8", "B9", "B10"]
MAX_DIM_PX, MIN_DIM_PX = 1200, 400
REPORT_PATH = ROOT / "data" / "output" / "Track1_geometric_evidence" / "local_crop_test_report.json"


def _find_reinforcement_dxf() -> Path:
    for p in RUN_ROOT.rglob("*.dxf"):
        if "reinforc" in p.name.lower() or "stirrup" in p.name.lower():
            return p
    raise FileNotFoundError("no reinforcement dxf found")


def _ink_density(png_path: Path) -> dict:
    img = np.array(Image.open(png_path).convert("L"))
    total = img.size
    ink = int(np.sum(img < 250))
    return {
        "w": int(img.shape[1]),
        "h": int(img.shape[0]),
        "ink_px": ink,
        "ink_pct": round(100.0 * ink / total, 3),
    }


def main() -> None:
    render_dxf_region_to_png = load_dxf_renderer()

    dxf = _find_reinforcement_dxf()
    doc = ezdxf.readfile(str(dxf))
    msp = doc.modelspace()

    ann = json.loads(
        (OUT_ROOT / "PhaseR.1_generalized_reinforcement_discovery" / "reinforcement_annotations.json")
        .read_text(encoding="utf-8")
    )
    annotations_by_beam = ann.get("by_beam") or {}

    extents = compute_extents_for_beams(
        list(annotations_by_beam.keys()), annotations_by_beam, msp
    )

    # --- Part B: purge stale artefacts for the test set ---
    purged = []
    for bid in TEST_BEAMS:
        for suffix in ("_crop.png", "_notext.png"):
            for prefix in (bid, f"Set1_{bid}"):
                p = CROP_DIR / f"{prefix}{suffix}"
                if p.exists():
                    old_size = p.stat().st_size
                    p.unlink()
                    purged.append({"path": str(p), "old_size_bytes": old_size})

    CROP_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for bid in TEST_BEAMS:
        ext_info = extents[bid]
        row: dict = {"beam_id": bid, "extent_info": ext_info}
        if ext_info["extent"] is None:
            row["error"] = "no_extent"
            results.append(row)
            continue

        t0 = time.time()
        crop_path = CROP_DIR / f"Set1_{bid}_crop.png"
        notext_path = CROP_DIR / f"Set1_{bid}_notext.png"

        xf_crop = render_dxf_region_to_png(
            dxf, crop_path, ext_info["extent"],
            max_dim_px=MAX_DIM_PX, min_dim_px=MIN_DIM_PX, render_text=True,
        )
        xf_notext = render_dxf_region_to_png(
            dxf, notext_path, ext_info["extent"],
            max_dim_px=MAX_DIM_PX, min_dim_px=MIN_DIM_PX, render_text=False,
        )
        elapsed = time.time() - t0

        row.update({
            "crop_path": str(crop_path),
            "notext_path": str(notext_path),
            "crop_dims": [xf_crop.img_w, xf_crop.img_h],
            "notext_dims": [xf_notext.img_w, xf_notext.img_h],
            "notext_ink": _ink_density(notext_path),
            "crop_ink": _ink_density(crop_path),
            "elapsed_s": round(elapsed, 3),
            "crop_size_bytes": crop_path.stat().st_size,
            "notext_size_bytes": notext_path.stat().st_size,
            "crop_mtime": crop_path.stat().st_mtime,
            "notext_mtime": notext_path.stat().st_mtime,
        })
        results.append(row)

    report = {
        "model_version": "9.3.3",
        "test_beams": TEST_BEAMS,
        "max_dim_px": MAX_DIM_PX,
        "min_dim_px": MIN_DIM_PX,
        "purged_files": purged,
        "results": results,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
