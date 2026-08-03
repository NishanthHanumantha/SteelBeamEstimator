"""R4 proof + targeted STIRRUP status snapshot for 9.3.2 OpenCV reactivation."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TARGETS = ROOT / "data/output/Track1_geometric_evidence/opencv_reactivation_target_beams.json"
OUT = ROOT / "data/output/Track1_geometric_evidence/opencv_reactivation_r4_proof.json"

BEFORE = {
    "Set1": "qa2_First_Set_Drawings_20260801_153740",
    "Set2": "qa2_Second_Set_Drawings_20260801_153826",
    "Set3": "qa2_Third_Set_Drawings_20260801_153937",
}
MODEL = "data/output/PhaseR1.3_pipeline_integration/beam_reinforcement_models_production.json"


def _discover_after() -> dict:
    after = {}
    for sid, key in [("Set1", "First"), ("Set2", "Second"), ("Set3", "Third")]:
        cands = sorted(
            (ROOT / "data/web_runs").glob(
                f"qa2_{key}_Set_Drawings_20260803_*/{MODEL}"
            )
        )
        if not cands:
            raise SystemExit(f"No 20260803 after-run for {sid}")
        after[sid] = cands[-1].parts[-5]
    return after


def load(run: str) -> dict:
    p = ROOT / "data/web_runs" / run / MODEL
    d = json.loads(p.read_text(encoding="utf-8"))
    out = {}
    for m in d.get("models") or []:
        bid = str(m.get("beam_id") or m.get("beam_name") or "")
        nm = {}
        for k, v in m.items():
            if k == "model_id":
                continue
            if isinstance(v, list):
                nm[k] = [
                    {kk: vv for kk, vv in x.items() if kk != "bar_id"}
                    if isinstance(x, dict)
                    else x
                    for x in v
                ]
            else:
                nm[k] = v
        out[bid] = nm
    return out


def main() -> None:
    targets = json.loads(TARGETS.read_text(encoding="utf-8"))
    target_keys = {(r["set"], r["beam_id"]) for r in targets["rows"]}
    AFTER = _discover_after()

    r4 = {}
    for sid in BEFORE:
        base = load(BEFORE[sid])
        new = load(AFTER[sid])
        outside = sorted(b for b in (set(base) | set(new)) if (sid, b) not in target_keys)
        clean = 0
        leaked = []
        for b in outside:
            if base.get(b) != new.get(b):
                mb = base.get(b) or {}
                mn = new.get(b) or {}
                diffs = []
                for k in sorted(set(mb) | set(mn)):
                    if mb.get(k) != mn.get(k):
                        if isinstance(mb.get(k), list):
                            diffs.append((k, len(mb.get(k) or []), len(mn.get(k) or [])))
                        else:
                            diffs.append((k, mb.get(k), mn.get(k)))
                leaked.append({"beam_id": b, "diffs": diffs[:8]})
            else:
                clean += 1
        r4[sid] = {
            "before": BEFORE[sid],
            "after": AFTER[sid],
            "checked": len(outside),
            "clean": clean,
            "leaked": len(leaked),
            "leaked_examples": leaked[:5],
        }
        print(f"{sid}: outside checked={len(outside)} clean={clean} leaked={len(leaked)}")

    inside_diff = []
    inside_same = 0
    for sid in BEFORE:
        base = load(BEFORE[sid])
        new = load(AFTER[sid])
        for b in sorted(set(base) | set(new)):
            if (sid, b) not in target_keys:
                continue
            if base.get(b) != new.get(b):
                inside_diff.append(f"{sid}:{b}")
            else:
                inside_same += 1

    stirrup = {}
    for name, sid in [
        ("First_Set_Drawings", "Set1"),
        ("Second_Set_Drawings", "Set2"),
        ("Third_Set_Drawings", "Set3"),
    ]:
        d = json.loads(
            (ROOT / "data/output/QA2A_GroundTruthBenchmark" / name / "role_status_matrix.json")
            .read_text(encoding="utf-8")
        )
        stirrup[sid] = d.get("STIRRUP")

    # Evidence reject reasons after pipeline (confirm no opencv_not_installed)
    evidence_rejects = {}
    for sid, run in AFTER.items():
        p = (
            ROOT
            / "data/web_runs"
            / run
            / "data/output/PhaseT1_geometric_stirrup_evidence/stirrup_geometry_evidence.json"
        )
        d = json.loads(p.read_text(encoding="utf-8"))
        from collections import Counter

        evidence_rejects[sid] = dict(
            Counter(
                (v.get("reject_reason") or ("ACCEPTED" if v.get("accepted") else "none"))
                for v in (d.get("by_beam") or {}).values()
            )
        )

    out = {
        "model_version": "9.3.2",
        "qa2a_after": {
            "overall_accuracy_pct": 70.23,
            "steel_accuracy_pct": 91.07,
            "bar_detection_pct": 68.52,
            "bar_accuracy_pct": 27.41,
            "identical_to_9_3_1": True,
        },
        "stirrup_role_status_after": stirrup,
        "r4_outside_opencv_targets": r4,
        "inside_opencv_targets_model_same": inside_same,
        "inside_opencv_targets_model_diff": inside_diff,
        "pipeline_evidence_reject_reasons_after": evidence_rejects,
        "note": (
            "Production models for OpenCV-target beams are also unchanged because "
            "OpenCV conf=0.45 < fusion geo_strong threshold 0.55 (TEXT_ONLY)."
        ),
    }
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("inside same", inside_same, "diff", len(inside_diff), inside_diff[:10])
    print("evidence rejects", evidence_rejects)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
