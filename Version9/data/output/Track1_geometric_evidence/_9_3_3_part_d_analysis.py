"""
9.3.3 Part D — before(9.3.2)/after(9.3.3) comparison for the T1 OpenCV
fallback crop-mechanism fix, across the 3-set opencv_reactivation scope.

Read-only analysis: consumes the backed-up 9.3.2 stirrup_geometry_evidence.json
(Track1_geometric_evidence/_9_3_2_before_backup/{Set}) and the freshly
regenerated 9.3.3 stirrup_geometry_evidence.json (web_runs/.../data/output/
PhaseT1_geometric_stirrup_evidence). Does not touch detection code.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # Version9
BEFORE_ROOT = ROOT / "data" / "output" / "Track1_geometric_evidence" / "_9_3_2_before_backup"
WEB_RUNS = ROOT / "data" / "web_runs"

SETS = {
    "Set1": "qa2_First_Set_Drawings_20260803_132045",
    "Set2": "qa2_Second_Set_Drawings_20260803_132207",
    "Set3": "qa2_Third_Set_Drawings_20260803_132502",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _ink_stats(render_dir: Path, beam_ids: list) -> dict:
    import numpy as np
    from PIL import Image

    out = {}
    for bid in beam_ids:
        p = render_dir / f"{bid}_notext.png"
        if not p.exists():
            continue
        img = np.array(Image.open(p).convert("L"))
        ink_pct = round(100.0 * float((img < 250).sum()) / float(img.size), 4)
        out[bid] = {"ink_pct": ink_pct, "w": int(img.shape[1]), "h": int(img.shape[0])}
    return out


def main() -> None:
    report = {"sets": {}}
    for set_id, run_name in SETS.items():
        before_path = BEFORE_ROOT / set_id / "stirrup_geometry_evidence.json"
        after_path = WEB_RUNS / run_name / "data" / "output" / "PhaseT1_geometric_stirrup_evidence" / "stirrup_geometry_evidence.json"
        before = _load(before_path)
        after = _load(after_path)

        before_beams = before.get("by_beam") or {}
        after_beams = after.get("by_beam") or {}

        reject_before = {}
        reject_after = {}
        changed = []
        for bid in sorted(set(before_beams) | set(after_beams)):
            b = before_beams.get(bid, {})
            a = after_beams.get(bid, {})
            rb = "ACCEPTED" if b.get("accepted") else (b.get("reject_reason") or "unknown")
            ra = "ACCEPTED" if a.get("accepted") else (a.get("reject_reason") or "unknown")
            reject_before[rb] = reject_before.get(rb, 0) + 1
            reject_after[ra] = reject_after.get(ra, 0) + 1
            if bool(b.get("accepted")) != bool(a.get("accepted")) or rb != ra:
                changed.append({
                    "beam_id": bid,
                    "before_method": b.get("detection_method"),
                    "before_accepted": bool(b.get("accepted")),
                    "before_reason": rb,
                    "after_method": a.get("detection_method"),
                    "after_accepted": bool(a.get("accepted")),
                    "after_reason": ra,
                    "after_median_pitch_mm": a.get("median_pitch_mm"),
                    "after_crop_ink_pct": a.get("crop_ink_pct"),
                })

        render_dir = WEB_RUNS / run_name / "data" / "output" / "PhaseT1_geometric_stirrup_evidence" / "opencv_renders"
        ink_after = _ink_stats(render_dir, sorted(set(before_beams) | set(after_beams)))
        invalid_after = [bid for bid, v in ink_after.items() if v["ink_pct"] < 0.2]

        report["sets"][set_id] = {
            "residual_before": before.get("residual_beam_count"),
            "residual_after": after.get("residual_beam_count"),
            "accepted_before": sum(1 for b in before_beams.values() if b.get("accepted")),
            "accepted_after": sum(1 for b in after_beams.values() if b.get("accepted")),
            "reject_reason_dist_before": reject_before,
            "reject_reason_dist_after": reject_after,
            "changed_beams": changed,
            "changed_count": len(changed),
            "notext_ink_pct_after": ink_after,
            "crop_invalid_after_count": len(invalid_after),
            "crop_invalid_after_beams": invalid_after,
        }

    out_path = ROOT / "data" / "output" / "Track1_geometric_evidence" / "part_d_before_after_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
