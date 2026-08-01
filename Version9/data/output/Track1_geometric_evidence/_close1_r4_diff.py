"""
CLOSE-1 — R4 scope-leakage proof.
Compares beam_reinforcement_models_production.json between the 9.2.0
baseline run and the latest 9.3.0 (flag-on) run, for beams NOT in the
residual target list. Report byte/row-level diffs.
"""
import json
from pathlib import Path

ROOT = Path(".")
RESIDUAL = json.loads(
    (ROOT / "Version9/data/output/Track1_geometric_evidence/residual_target_beams.json")
    .read_text(encoding="utf-8")
)

BASELINE_RUNS = {
    "Set1": "qa2_First_Set_Drawings_20260801_103357",
    "Set2": "qa2_Second_Set_Drawings_20260801_103505",
    "Set3": "qa2_Third_Set_Drawings_20260801_103630",
}
LATEST_930_RUNS = {
    "Set1": "qa2_First_Set_Drawings_20260801_152514",
    "Set2": "qa2_Second_Set_Drawings_20260801_152612",
    "Set3": "qa2_Third_Set_Drawings_20260801_152811",
}

MODEL_REL = "data/output/PhaseR1.3_pipeline_integration/beam_reinforcement_models_production.json"


def residual_beam_ids(set_id):
    out = set()
    for r in RESIDUAL.get("rows") or []:
        if r.get("included") and r.get("set_id") == set_id:
            out.add(str(r.get("beam_id")))
    return out


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
    """Strip volatile identifiers (bar_id/detail_id with random hex, timestamps)
    to compare engineering content, not synthetic IDs."""
    if not isinstance(row, dict):
        return row
    skip_keys = {"bar_id"}
    return {k: v for k, v in row.items() if k not in skip_keys}


L2_KEYS = None  # discover dynamically


def diff_beam(m_base, m_new):
    """Return list of (field, base_val, new_val) diffs at beam level."""
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
        new_run = LATEST_930_RUNS[set_id]
        base = load_models(base_run)
        new = load_models(new_run)
        residual = residual_beam_ids(set_id)

        all_beams = sorted(set(base.keys()) | set(new.keys()))
        out_of_scope = [b for b in all_beams if b not in residual]

        checked = 0
        clean = 0
        leaked = []
        for bid in out_of_scope:
            checked += 1
            mb = base.get(bid)
            mn = new.get(bid)
            if mb is None or mn is None:
                leaked.append({"beam_id": bid, "issue": "beam_missing_in_one_run",
                                "in_base": mb is not None, "in_new": mn is not None})
                continue
            d = diff_beam(mb, mn)
            if not d:
                clean += 1
            else:
                leaked.append({"beam_id": bid, "diffs": d})

        report[set_id] = {
            "base_run": base_run,
            "new_run": new_run,
            "residual_beams_excluded": len(residual),
            "out_of_scope_checked": checked,
            "clean": clean,
            "leaked_count": len(leaked),
            "leaked": leaked,
        }

    out_path = ROOT / "Version9/data/output/Track1_geometric_evidence/close1_r4_scope_leakage.json"
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    for set_id, r in report.items():
        print(f"{set_id}: checked={r['out_of_scope_checked']} clean={r['clean']} leaked={r['leaked_count']}")
        for l in r["leaked"][:10]:
            print("   ", l)


if __name__ == "__main__":
    main()
