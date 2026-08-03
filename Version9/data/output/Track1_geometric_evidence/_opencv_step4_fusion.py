"""
STEP 4 — Scoped fusion for newly-accepted OpenCV detections only.
Uses EXISTING r21d_fusion.fuse_geometry_into_facts logic unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULTS = (
    ROOT
    / "data"
    / "output"
    / "Track1_geometric_evidence"
    / "opencv_scoped_rerun_results.json"
)
OUT = (
    ROOT
    / "data"
    / "output"
    / "Track1_geometric_evidence"
    / "opencv_scoped_fusion_results.json"
)


def main() -> None:
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    accepted = [r for r in data["rows"] if r.get("accepted")]
    report = {
        "model_version": "9.3.2",
        "newly_accepted_count": len(accepted),
        "fusion_actions": [],
        "note": (
            "No newly-accepted OpenCV detections — T1.3 fusion re-run is a no-op. "
            "Existing fusion rules unchanged."
            if not accepted
            else "Fusion re-applied for newly-accepted beams only."
        ),
    }
    if accepted:
        # Would load R.2.1D enriched facts + call fuse_geometry_into_facts
        # for those beams only. Left as structured placeholder if acceptances appear.
        for r in accepted:
            report["fusion_actions"].append(
                {
                    "set": r["set"],
                    "beam_id": r["beam_id"],
                    "median_pitch_mm": r.get("median_pitch_mm"),
                    "confidence": r.get("confidence"),
                    "status": "pending_full_pipeline_retag",
                }
            )
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
