"""
CLOSE-2 — R6 flag-off equivalence.
Compares beam_reinforcement_models_production.json between the 9.2.0
baseline run and the flag-off (enable_geometry_stirrup_evidence=false)
9.3.0 run, for ALL beams (full equivalence, not just out-of-scope).
"""
import json
from pathlib import Path

ROOT = Path(".")

BASELINE_RUNS = {
    "Set1": "qa2_First_Set_Drawings_20260801_103357",
    "Set2": "qa2_Second_Set_Drawings_20260801_103505",
    "Set3": "qa2_Third_Set_Drawings_20260801_103630",
}
FLAGOFF_RUNS = {
    "Set1": "qa2_First_Set_Drawings_20260801_153444",
    "Set2": "qa2_Second_Set_Drawings_20260801_153515",
    "Set3": "qa2_Third_Set_Drawings_20260801_153556",
}

MODEL_REL = "data/output/PhaseR1.3_pipeline_integration/beam_reinforcement_models_production.json"


def load_models(run_name):
    p = ROOT / "Version9/data/web_runs" / run_name / MODEL_REL
    d = json.loads(p.read_text(encoding="utf-8"))
    models = d.get("models") or []
    by_beam = {}
    for m in models:
        bid = str(m.get("beam_id") or m.get("beam_name") or "")
        by_beam[bid] = m
    return by_beam


def normalize_row(row):
    if not isinstance(row, dict):
        return row
    skip_keys = {"bar_id"}
    return {k: v for k, v in row.items() if k not in skip_keys}


def diff_beam(m_base, m_new):
    diffs = []
    keys = sorted(set(m_base.keys()) | set(m_new.keys()))
    for k in keys:
        if k in ("model_id",):
            continue
        vb = m_base.get(k)
        vn = m_new.get(k)
        if isinstance(vb, list) and isinstance(vn, list):
            nb = [normalize_row(x) for x in vb]
            nn = [normalize_row(x) for x in vn]
            if nb != nn:
                diffs.append((k, len(vb), len(vn)))
        else:
            if vb != vn:
                diffs.append((k, vb, vn))
    return diffs


def main():
    report = {}
    for set_id, base_run in BASELINE_RUNS.items():
        new_run = FLAGOFF_RUNS[set_id]
        base = load_models(base_run)
        new = load_models(new_run)

        all_beams = sorted(set(base.keys()) | set(new.keys()))
        checked = 0
        clean = 0
        diffs_found = []
        for bid in all_beams:
            checked += 1
            mb = base.get(bid)
            mn = new.get(bid)
            if mb is None or mn is None:
                diffs_found.append({"beam_id": bid, "issue": "beam_missing_in_one_run",
                                     "in_base": mb is not None, "in_new": mn is not None})
                continue
            d = diff_beam(mb, mn)
            if not d:
                clean += 1
            else:
                diffs_found.append({"beam_id": bid, "diffs": d})

        report[set_id] = {
            "base_run": base_run,
            "flagoff_run": new_run,
            "total_beams_checked": checked,
            "clean": clean,
            "diff_count": len(diffs_found),
            "diffs": diffs_found,
        }

    out_path = ROOT / "Version9/data/output/Track1_geometric_evidence/close2_r6_flagoff_equivalence.json"
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    for set_id, r in report.items():
        print(f"{set_id}: checked={r['total_beams_checked']} clean={r['clean']} diffs={r['diff_count']}")
        for l in r["diffs"][:15]:
            print("   ", l)


if __name__ == "__main__":
    main()
