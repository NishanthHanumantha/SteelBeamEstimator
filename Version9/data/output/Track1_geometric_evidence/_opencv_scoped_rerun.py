"""
9.3.2 — Scoped OpenCV reactivation re-run.

Re-runs EXISTING T1.2 path (vector → section → OpenCV fallback) ONLY for
beams in opencv_reactivation_target_beams.json. No threshold/fusion/zone
algorithm changes.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # Version9
ENGINE = ROOT
SYS_SRC = ENGINE / "src"
if str(SYS_SRC) not in sys.path:
    sys.path.insert(0, str(SYS_SRC))

TARGET = (
    ENGINE
    / "data"
    / "output"
    / "Track1_geometric_evidence"
    / "opencv_reactivation_target_beams.json"
)
OUT_DIR = ENGINE / "data" / "output" / "PhaseT1_geometric_stirrup_evidence"
CROP_DIR = OUT_DIR / "opencv_renders"
RESULTS = (
    ENGINE
    / "data"
    / "output"
    / "Track1_geometric_evidence"
    / "opencv_scoped_rerun_results.json"
)

# Latest flag-on web runs that produced the target list
SOURCE_RUNS = {
    "Set1": "qa2_First_Set_Drawings_20260801_153740",
    "Set2": "qa2_Second_Set_Drawings_20260801_153826",
    "Set3": "qa2_Third_Set_Drawings_20260801_153937",
}


def _load_orch(run_name: str):
    import importlib.util

    pkg = SYS_SRC / "PhaseT1_geometric_stirrup_evidence"
    # Ensure package import works
    alias = "PhaseT1_scoped"
    init = pkg / "__init__.py"
    if alias not in sys.modules:
        # Load as package-ish by adding src and importing normally
        pass
    from PhaseT1_geometric_stirrup_evidence.phase_t1_orchestrator import (  # type: ignore
        PhaseT1Orchestrator,
    )

    run_root = ENGINE / "data" / "web_runs" / run_name
    output_root = run_root / "data" / "output"
    return PhaseT1Orchestrator(ENGINE, run_root, output_root)


def main() -> None:
    import cv2

    targets = json.loads(TARGET.read_text(encoding="utf-8"))
    rows = targets["rows"]
    by_set: dict[str, list] = {}
    for r in rows:
        by_set.setdefault(r["set"], []).append(r)

    CROP_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_results = []
    t_global = time.time()

    for set_id, beams in sorted(by_set.items()):
        run_name = SOURCE_RUNS[set_id]
        orch = _load_orch(run_name)
        dxf = orch._find_reinforcement_dxf()
        beam_boxes = orch._load_beam_bboxes()
        text_spacing = orch._load_text_spacings()
        det_cfg = orch.cfg.get("detection") or {}

        import ezdxf
        from PhaseT1_geometric_stirrup_evidence.vector_stirrup_detector import (
            detect_elevation_ticks,
            detect_section_rectangles,
        )

        msp = ezdxf.readfile(str(dxf)).modelspace() if dxf else None

        for row in beams:
            bid = row["beam_id"]
            t0 = time.time()
            bbox = beam_boxes.get(bid)
            text_sp = text_spacing.get(bid)
            result = {
                "beam_id": bid,
                "set": set_id,
                "source_run": run_name,
                "prior_fallback_reason": row.get("prior_fallback_reason"),
                "target_groups": row.get("target_groups"),
                "bbox_present": bbox is not None,
                "dxf_present": dxf is not None,
            }
            if not bbox or msp is None or dxf is None:
                result.update(
                    {
                        "detection_method": "none",
                        "accepted": False,
                        "reject_reason": "missing_bbox_or_dxf",
                        "confidence": 0.0,
                        "elapsed_s": round(time.time() - t0, 4),
                    }
                )
                all_results.append(result)
                continue

            # Same decision order as PhaseT1Orchestrator.run (unchanged logic)
            elev = detect_elevation_ticks(
                msp, bbox, cfg=det_cfg, text_spacing_mm=text_sp
            )
            chosen = None
            path_used = None
            if elev.get("accepted"):
                chosen = elev
                path_used = "vector_elevation_ticks"
            else:
                sec = detect_section_rectangles(msp, bbox)
                if sec.get("accepted"):
                    chosen = sec
                    path_used = "vector_section"
                else:
                    fb = orch._opencv_for_beam(
                        dxf,
                        bid,
                        bbox,
                        det_cfg,
                        text_sp,
                        reason=elev.get("reject_reason") or "vector_rejected",
                    )
                    chosen = fb
                    path_used = "opencv_fallback"
                    # Copy crop into engine-level opencv_renders for spot-check
                    src_crop = (
                        orch.out_dir / "opencv_renders" / f"{bid}_crop.png"
                    )
                    # Namespace crops by set to avoid Set1/Set2 beam_id collisions
                    dst_crop = CROP_DIR / f"{set_id}_{bid}_crop.png"
                    if src_crop.exists():
                        shutil.copy2(src_crop, dst_crop)
                        result["crop_path"] = str(dst_crop)
                    else:
                        # full notext may exist even if crop failed
                        src_full = (
                            orch.out_dir / "opencv_renders" / f"{bid}_notext.png"
                        )
                        if src_full.exists():
                            dst_full = CROP_DIR / f"{set_id}_{bid}_notext.png"
                            shutil.copy2(src_full, dst_full)
                            result["notext_path"] = str(dst_full)

            assert chosen is not None
            result.update(
                {
                    "path_used": path_used,
                    "detection_method": chosen.get("detection_method"),
                    "accepted": bool(chosen.get("accepted")),
                    "reject_reason": chosen.get("reject_reason"),
                    "fallback_reason": chosen.get("fallback_reason"),
                    "median_pitch_mm": chosen.get("median_pitch_mm"),
                    "confidence": chosen.get("confidence"),
                    "tick_count": len(chosen.get("tick_positions_mm") or []),
                    "measured_pitch_mm": chosen.get("measured_pitch_mm"),
                    "text_spacing_agreement": chosen.get("text_spacing_agreement"),
                    "text_spacing_mm": chosen.get("text_spacing_mm"),
                    "cv2_version": cv2.__version__,
                    "elapsed_s": round(time.time() - t0, 4),
                    "raw": {
                        k: chosen.get(k)
                        for k in (
                            "detection_method",
                            "accepted",
                            "reject_reason",
                            "fallback_reason",
                            "median_pitch_mm",
                            "confidence",
                            "tick_positions_mm",
                            "measured_pitch_mm",
                            "text_spacing_agreement",
                            "pitch_cv",
                            "zone_count_estimate",
                            "zone_boundaries_mm",
                            "zone_pitches_mm",
                        )
                        if k in chosen
                    },
                }
            )
            all_results.append(result)
            print(
                f"{set_id} {bid}: method={result['detection_method']} "
                f"accepted={result['accepted']} "
                f"reject={result.get('reject_reason')} "
                f"pitch={result.get('median_pitch_mm')} "
                f"conf={result.get('confidence')} "
                f"t={result['elapsed_s']}s"
            )

    elapsed = round(time.time() - t_global, 3)
    accepted = [r for r in all_results if r.get("accepted")]
    still_dead = [
        r for r in all_results if r.get("reject_reason") == "opencv_not_installed"
    ]
    reject_counts = Counter(
        r.get("reject_reason") for r in all_results if not r.get("accepted")
    )
    method_counts = Counter(r.get("detection_method") for r in all_results)

    summary = {
        "model_version": "9.3.2",
        "cv2_version": cv2.__version__,
        "target_count": len(all_results),
        "accepted_count": len(accepted),
        "opencv_not_installed_remaining": len(still_dead),
        "method_counts": dict(method_counts),
        "reject_reason_counts": dict(reject_counts),
        "elapsed_s": elapsed,
        "avg_s_per_beam": round(elapsed / max(len(all_results), 1), 4),
        "accepted_beams": [
            {
                "set": r["set"],
                "beam_id": r["beam_id"],
                "median_pitch_mm": r.get("median_pitch_mm"),
                "confidence": r.get("confidence"),
                "tick_count": r.get("tick_count"),
                "text_spacing_agreement": r.get("text_spacing_agreement"),
            }
            for r in accepted
        ],
        "rows": all_results,
    }
    RESULTS.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print("=== SUMMARY ===")
    print(json.dumps({k: summary[k] for k in summary if k != "rows"}, indent=2))
    print("wrote", RESULTS)


if __name__ == "__main__":
    main()
