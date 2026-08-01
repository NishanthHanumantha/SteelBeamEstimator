"""
CLOSE-3 — WRONG_QTY regression attribution (100 -> 113).
Classify every 9.3.0 STIRRUP WRONG_QUANTITY row into A/B/C/D.
"""
import json
from pathlib import Path

ROOT = Path(".")  # Version9/
RESIDUAL = json.loads(
    (ROOT / "data/output/Track1_geometric_evidence/residual_target_beams.json")
    .read_text(encoding="utf-8")
)

SET_DIRS = {
    "Set1": "First_Set_Drawings",
    "Set2": "Second_Set_Drawings",
    "Set3": "Third_Set_Drawings",
}

# index residual rows by (set_id, beam_id) -> list of rows (STIRRUP only, since
# residual list is built entirely from STIRRUP MISSING/WRONG_QTY baseline rows)
residual_index = {}
for r in RESIDUAL.get("rows") or []:
    key = (r["set_id"], r["beam_id"])
    residual_index.setdefault(key, []).append(r)


def classify(set_id, row):
    beam_id = row["beam_id"]
    key = (set_id, beam_id)
    residual_rows = residual_index.get(key, [])
    included_rows = [r for r in residual_rows if r.get("included")]

    if not included_rows:
        return "C", "not in residual_target_beams.json (out-of-scope)", None, None

    baseline_rows = [
        {"target_group": r["target_group"], "current_status": r["current_status"],
         "current_qty": r["current_qty"], "gt_qty": r["gt_qty"], "diameter": r.get("diameter")}
        for r in included_rows
    ]

    gt_qty = row.get("estimator_qty")
    dia = row.get("diameter")

    # Match this specific 9.3.0 WRONG_QTY row to the baseline residual row that
    # represents the SAME ground-truth bar (same gt_qty, and diameter if available).
    exact = [r for r in included_rows if r.get("gt_qty") == gt_qty and (dia is None or r.get("diameter") == dia)]
    if not exact:
        exact = [r for r in included_rows if r.get("gt_qty") == gt_qty]

    if exact:
        matched = exact[0]
        if matched["target_group"] == "TARGET_WRONG_QTY":
            return ("A",
                    "in-scope, was WRONG_QTY at baseline (T1.4 zone refinement changed the split but still not GT-matching)",
                    baseline_rows, matched)
        if matched["target_group"] == "TARGET_MISSING":
            return ("B",
                    "in-scope, was MISSING (qty=0) at baseline; T1 geometry synthesis now produces a nonzero qty that does not match GT (partial detection, not a full fix)",
                    baseline_rows, matched)
        return "A", "in-scope (other target group)", baseline_rows, matched

    # Beam is residual but this specific gt_qty doesn't match any baseline row
    # (ambiguous row-level mapping) — fall back to beam-level group inference.
    groups = {r["target_group"] for r in included_rows}
    if "TARGET_WRONG_QTY" in groups:
        return "A", "in-scope beam (row-level GT match ambiguous; beam had TARGET_WRONG_QTY at baseline)", baseline_rows, None
    if "TARGET_MISSING" in groups:
        return "B", "in-scope beam (row-level GT match ambiguous; beam had TARGET_MISSING at baseline)", baseline_rows, None
    return "A", "in-scope (ambiguous)", baseline_rows, None


def main():
    all_rows = []
    for set_id, dirname in SET_DIRS.items():
        p = ROOT / "data/output/QA2A_GroundTruthBenchmark" / dirname / "bar_matching.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        for row in d["rows"]:
            if row.get("bar_role") != "STIRRUP" or row.get("status") != "WRONG_QUANTITY":
                continue
            cat, mech, baseline, matched = classify(set_id, row)
            all_rows.append({
                "set_id": set_id,
                "beam_id": row["beam_id"],
                "category": cat,
                "mechanism": mech,
                "model_qty": row.get("model_qty"),
                "estimator_qty": row.get("estimator_qty"),
                "model_diameter": row.get("model_diameter"),
                "diameter": row.get("diameter"),
                "is_synthesized_geometry": row.get("is_synthesized_geometry"),
                "matched_baseline_row": matched,
                "baseline_residual_rows": baseline,
            })

    by_cat = {}
    for r in all_rows:
        by_cat.setdefault(r["category"], []).append(r)

    # For Category A: did the new qty move closer to or further from GT vs baseline?
    a_closer = a_further = a_same = a_unknown = 0
    for r in by_cat.get("A", []):
        mb = r.get("matched_baseline_row")
        if not mb or mb.get("current_qty") is None or r.get("model_qty") is None or r.get("estimator_qty") is None:
            a_unknown += 1
            continue
        old_err = abs(mb["current_qty"] - r["estimator_qty"])
        new_err = abs(r["model_qty"] - r["estimator_qty"])
        if new_err < old_err:
            a_closer += 1
        elif new_err > old_err:
            a_further += 1
        else:
            a_same += 1

    summary = {
        "total_wrong_qty_stirrup_rows": len(all_rows),
        "by_category_count": {k: len(v) for k, v in sorted(by_cat.items())},
        "by_category_by_set": {
            k: {sid: sum(1 for r in v if r["set_id"] == sid) for sid in SET_DIRS}
            for k, v in by_cat.items()
        },
        "category_a_direction": {
            "closer_to_gt": a_closer,
            "further_from_gt": a_further,
            "unchanged": a_same,
            "unknown": a_unknown,
        },
        "rows": all_rows,
    }

    out_path = ROOT / "data/output/Track1_geometric_evidence/close3_wrong_qty_attribution.json"
    out_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print("TOTAL:", summary["total_wrong_qty_stirrup_rows"])
    print("By category:", summary["by_category_count"])
    print("By category by set:", json.dumps(summary["by_category_by_set"], indent=2))
    print("Category A direction (vs baseline qty error):", summary["category_a_direction"])
    for cat in sorted(by_cat):
        print(f"\n=== Category {cat} examples ===")
        for r in by_cat[cat][:5]:
            print(" ", r["set_id"], r["beam_id"], "model_qty=", r["model_qty"], "gt_qty=", r["estimator_qty"],
                  "synth=", r["is_synthesized_geometry"], "baseline=", r["baseline_residual_rows"])


if __name__ == "__main__":
    main()
